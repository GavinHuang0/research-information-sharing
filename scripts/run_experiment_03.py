"""Execute the prespecified PCA/coefficient-history surface in auditable stages.

No calibration or power study is run. Earlier/later samples are both seen-period
exploration; freezes ensure reproducibility, not a fresh holdout claim.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv/matplotlib-cache"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
from factorcast.data import load_daily_returns
from factorcast.pilot import S, prepare_panels
from factorcast.surface import cell_inventory, run_stage
from factorcast.surface_bootstrap import run_inference
from factorcast.surface_reporting import write_reports


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_write(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True, default=str) + "\n").encode())


def fingerprint(config_bytes):
    paths = sorted((ROOT / "src/factorcast").glob("*.py")) + [Path(__file__).resolve()]
    paths += [ROOT / name for name in ("scripts/audit_experiment_03.py", "requirements-lock.txt",
              "requirements-analysis-lock.txt", "experiments/03-pca-history-surface/protocol.md",
              "configs/experiment_03_plan.toml")]
    paths += sorted((ROOT / "tests").glob("test_*.py"))
    return dict(config_sha256_lf=sha(config_bytes.replace(b"\r\n", b"\n")),
                code_and_protocol_sha256_lf={p.relative_to(ROOT).as_posix(): sha(p.read_bytes().replace(b"\r\n", b"\n")) for p in paths},
                versions={name: version(name) for name in ("numpy", "pandas", "scipy", "scikit-learn", "matplotlib")})


def validate_config(config):
    if config["execution"]["source_plan"] != "configs/experiment_03_plan.toml":
        raise ValueError("The original Experiment 3 planning source is fixed")
    plan = tomllib.loads((ROOT / config["execution"]["source_plan"]).read_text(encoding="utf-8"))
    scientific = lambda x: {k: v for k, v in x.items() if k not in {"plan", "execution"}}
    if scientific(config) != scientific(plan):
        raise ValueError("Executable settings must preserve the immutable scientific plan")
    mutable = {"authorized_work", "implementation_run_bootstrap_or_calibration_now", "run_authorized",
               "calibration_authorized", "power_authorized", "source_plan", "source_planning_commit",
               "run_id", "authorized_date"}
    execution = lambda x: {k: v for k, v in x["execution"].items() if k not in mutable}
    if execution(config) != execution(plan):
        raise ValueError("Storage, audit, and other planned execution constraints changed")
    if (not config["plan"]["executable"] or not config["execution"]["run_authorized"]
            or config["execution"]["calibration_authorized"] or config["execution"]["power_authorized"]):
        raise ValueError("Only the authorized empirical experiment may execute")
    if tuple(config["design"]["targets"]) != S:
        raise ValueError("Fixed target order changed")
    boot = config["bootstrap"]
    if (boot["replicates"], boot["seed"], boot["expected_block_length_dates"], boot["sensitivity_block_lengths_dates"]) != (9999, 20261102, 13, [6, 26]):
        raise ValueError("Frozen bootstrap settings changed")


def check_manifest(directory):
    manifest = json.loads((directory / "stage_manifest.json").read_bytes())
    for name, expected in manifest["files"].items():
        expected = expected["sha256"] if isinstance(expected, dict) else expected
        if sha((directory / name).read_bytes()) != expected:
            raise ValueError(f"Changed output: {directory / name}")
    return manifest


def finish_stage(directory):
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix in {".csv", ".json", ".md", ".toml", ".txt"}:
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    files = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "stage_manifest.json":
            if path.stat().st_size >= 100_000_000:
                raise ValueError(f"Archive file exceeds declared limit: {path}")
            files[path.relative_to(directory).as_posix()] = sha(path.read_bytes())
    json_write(directory / "stage_manifest.json", dict(completed_at_utc=utc(), files=files))


def load_inputs(config):
    provenance = ROOT / config["data"]["provenance"]
    source = json.loads(provenance.read_bytes())
    inputs = dict(provenance=dict(path=provenance.relative_to(ROOT).as_posix(), sha256=sha(provenance.read_bytes())))
    returns = {}
    for weighting in ("value", "equal"):
        path = ROOT / config["data"][f"{weighting}_returns"]
        raw = path.read_bytes()
        if sha(raw) != source["panels"][weighting]["sha256"]:
            raise ValueError(f"Archived daily input changed: {weighting}")
        inputs[weighting] = dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(raw), bytes=len(raw))
        returns[weighting] = load_daily_returns(path, units="decimal")
    for name in ("fixed-pilot-2026-10-27", "experiment-02-2026-11-01"):
        path = ROOT / "results" / name / "artifact_manifest.json"
        archive = json.loads(path.read_bytes())
        for item in archive["files"]:
            if sha((ROOT / item["path"]).read_bytes()) != item["sha256"]:
                raise ValueError(f"Earlier experiment changed: {item['path']}")
        inputs[name] = dict(manifest_sha256=sha(path.read_bytes()), verified_files=len(archive["files"]))
    calendar = config["calendar"]
    prep = dict(design=dict(targets=list(S), small_panel=list(S)), data=config["data"],
                calendar=dict(origin_start=calendar["origin_start"], response_end=calendar["response_end"],
                              final_response_start=calendar["later_seen_response_start"]))
    datasets, report = prepare_panels(returns, prep)
    first = datasets["value"]
    if len(first.X) != 1377 or not first.origin_dates.equals(datasets["equal"].origin_dates):
        raise ValueError("Inherited common calendar changed")
    return inputs, datasets, report


def progress(record):
    print(json.dumps(dict(time_utc=utc(), **record), default=str), flush=True)


def inference_period(run, period, config):
    stage = run / period
    check_manifest(stage)
    dates = json.loads((stage / "dates.json").read_bytes())
    if tuple(dates["target_order"]) != S:
        raise ValueError("Target order changed")
    cells = pd.read_csv(stage / "cells.csv", keep_default_na=False)
    scratch = ROOT / ".venv/experiment03-losses" / period
    scratch.mkdir(parents=True, exist_ok=True)
    losses = {}
    for weighting in ("value", "equal"):
        predictions = np.load(stage / f"predictions_{weighting}.npy", mmap_mode="r")
        actual = np.load(stage / f"actual_{weighting}.npy", mmap_mode="r")
        loss_path = scratch / f"losses_{weighting}.npy"
        panel = np.lib.format.open_memmap(loss_path, mode="w+", dtype="float64", shape=predictions.shape)
        for start in range(0, len(cells), 32):
            stop = min(start + 32, len(cells))
            panel[:, start:stop, :] = (predictions[:, start:stop, :] - actual[:, None, :]) ** 2
        panel.flush()
        losses[weighting] = panel
    output = run / "inference" / period
    result, index_manifest = run_inference(losses, cells, dates["response_dates"], config=config, period=period, output=output)
    finish_stage(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment_03.toml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", required=True, choices=("freeze", "earlier_seen", "later_seen", "audit-earlier", "audit-later", "inference", "audit-inference", "report", "finalize"))
    args = parser.parse_args()
    config_bytes = args.config.read_bytes()
    config = tomllib.loads(config_bytes.decode())
    validate_config(config)
    run = args.output.resolve()
    current = fingerprint(config_bytes)
    inputs, datasets, calendar = load_inputs(config)
    if args.stage == "freeze":
        if run.exists():
            parser.error("Output exists; use a new experiment directory")
        for path in (ROOT / ".venv/experiment_03_validation.txt", ROOT / "docs/experiment_03_validation.md"):
            if not path.is_file():
                parser.error(f"Missing completed validation gate: {path}")
        validation_status = json.loads((ROOT / ".venv/experiment_03_validation_status.json").read_bytes())
        log_bytes = (ROOT / ".venv/experiment_03_validation.txt").read_bytes().replace(b"\r\n", b"\n")
        if (validation_status["status"] != "passed" or validation_status["tests_run"] < 91
                or validation_status["validation_log_sha256_lf"] != sha(log_bytes)):
            parser.error("Successful complete validation record is missing, stale, or inconsistent")
        run.mkdir(parents=True)
        for source, destination in ((args.config, "config.toml"), (ROOT / "configs/experiment_03_plan.toml", "planning_config.toml"),
                (ROOT / "experiments/03-pca-history-surface/protocol.md", "protocol.md"),
                (ROOT / "docs/experiment_03_validation.md", "preflight.md"),
                (ROOT / ".venv/experiment_03_validation.txt", "validation.txt"),
                (ROOT / ".venv/experiment_03_validation_status.json", "validation_status.json"),
                (ROOT / "results/experiment-02-2026-11-01/synthetic_validation.json", "inherited_calibration_diagnostics.json")):
            raw = source.read_bytes().replace(b"\r\n", b"\n")
            (run / destination).write_bytes(raw)
        cell_inventory(config).to_csv(run / "cells.csv", index=False, lineterminator="\n")
        json_write(run / "calendar.json", calendar)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
        json_write(run / "source_freeze.json", dict(frozen_at_utc=utc(), fingerprint=current, inputs=inputs,
                   implementation_commit=commit, planning_commit=config["execution"]["source_planning_commit"],
                   scientific_selection_permitted=False, all_evaluation_periods_already_seen=True,
                   calibration_and_power_status="deferred_not_run", finite_sample_calibration_established=False))
        json_write(run / "metadata.json", dict(started_at_utc=utc(), python=sys.version, fingerprint=current, inputs=inputs,
                   implementation_commit=commit, loss="squared next-week log-variance proxy forecast error",
                   earlier_seen_dates=718, later_seen_dates=87, distinct_factor_cells=936, own_references=20))
        print("Experiment 3 source/configuration/inputs frozen before empirical execution.", flush=True)
        return
    frozen = json.loads((run / "source_freeze.json").read_bytes())
    if frozen["fingerprint"] != current or frozen["inputs"] != inputs:
        parser.error("Frozen source/configuration/dependencies/inputs changed")
    if args.stage in {"earlier_seen", "later_seen"}:
        if args.stage == "later_seen":
            earlier = check_manifest(run / "earlier_seen")
            audit = json.loads((run / "audit_earlier_seen.json").read_bytes())
            if audit["status"] != "passed":
                parser.error("Earlier output audit must pass first")
            later_freeze = dict(frozen_at_utc=utc(), earlier_files=earlier["files"], fingerprint=current, no_winner_selection=True)
            if (run / "later_freeze.json").exists():
                parser.error("Later-stage freeze already exists; refusing overwrite")
            json_write(run / "later_freeze.json", later_freeze)
        output = run / args.stage
        output.mkdir(exist_ok=False)
        json_write(output / "started.json", dict(started_at_utc=utc(), stage=args.stage))
        manifest = run_stage(datasets, config, args.stage, output, progress=progress)
        check_manifest(output)
        print(json.dumps(dict(event="stage_complete", stage=args.stage, completed_at_utc=utc())), flush=True)
        return
    import audit_experiment_03 as audit
    if args.stage in {"audit-earlier", "audit-later"}:
        period = "earlier_seen" if args.stage == "audit-earlier" else "later_seen"
        audit.audit_stage(run, period, config, datasets)
    elif args.stage == "inference":
        frames = []
        for period in ("earlier_seen", "later_seen"):
            checked = json.loads((run / f"audit_{period}.json").read_bytes())
            if checked["status"] != "passed":
                parser.error("Both output audits must pass before inference")
            frames.append(inference_period(run, period, config))
            progress(dict(event="inference_period_complete", period=period, rows=len(frames[-1])))
        full = pd.concat(frames, ignore_index=True)
        full.to_csv(run / "inference/bootstrap_results.csv", index=False, float_format="%.17g", lineterminator="\n")
        anchors = full.loc[full.anchor.astype(bool)]
        anchors.to_csv(run / "inference/anchor_table.csv", index=False, float_format="%.17g", lineterminator="\n")
        finish_stage(run / "inference")
    elif args.stage == "audit-inference":
        audit.audit_inference(run, config)
    elif args.stage == "report":
        check_manifest(run / "inference")
        result = write_reports(run, config)
        finish_stage(run / "reports")
        print(json.dumps(dict(event="report_complete", outputs=result), default=str), flush=True)
    elif args.stage == "finalize":
        audit.finalize(run, config)


if __name__ == "__main__":
    main()
