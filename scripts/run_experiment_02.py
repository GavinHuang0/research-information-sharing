"""Reproduce the frozen bootstrap/history experiment in auditable stages.

Order: freeze, part-a, development, final, inference, report. The final stage
requires a development freeze, and every empirical stage checks the initial
source/config/data fingerprints. No final procedure or history is selected.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
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

import pandas as pd

from factorcast.bootstrap import run_inference
from factorcast.data import load_daily_returns
from factorcast.history import policies, run_stage
from factorcast.history_reporting import summarize_history, write_reports
from factorcast.pilot import S, prepare_panels


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_write(path: Path, value) -> None:
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True, default=str) + "\n").encode())


def fingerprint(config_bytes: bytes) -> dict:
    paths = sorted((ROOT / "src/factorcast").glob("*.py")) + [Path(__file__).resolve()]
    paths += [ROOT / "requirements-lock.txt", ROOT / "requirements-analysis-lock.txt",
              ROOT / "experiments/02-bootstrap-history/protocol.md", ROOT / "configs/experiment_02_plan.toml",
              ROOT / "scripts/validate_bootstrap_synthetic.py"]
    return dict(config_sha256_lf=sha(config_bytes.replace(b"\r\n", b"\n")),
                code_and_protocol_sha256_lf={path.relative_to(ROOT).as_posix(): sha(path.read_bytes().replace(b"\r\n", b"\n")) for path in paths},
                versions={name: version(name) for name in ("numpy", "pandas", "scipy", "scikit-learn", "matplotlib")})


def check_manifest(directory: Path) -> dict:
    manifest = json.loads((directory / "stage_manifest.json").read_bytes())
    for name, expected in manifest["files"].items():
        if sha((directory / name).read_bytes()) != expected:
            raise ValueError(f"Changed stage output: {directory / name}")
    return manifest


def finish_stage(directory: Path) -> None:
    for path in directory.rglob("*"):
        if path.is_file() and path.suffix in {".csv", ".json", ".md", ".toml", ".txt"}:
            contents = path.read_bytes()
            normalized = contents.replace(b"\r\n", b"\n")
            if normalized != contents:
                path.write_bytes(normalized)
    files = {path.relative_to(directory).as_posix(): sha(path.read_bytes()) for path in directory.rglob("*")
             if path.is_file() and path.name != "stage_manifest.json"}
    json_write(directory / "stage_manifest.json", dict(completed_at_utc=utc(), files=files))


def write_predictions(path: Path, frame: pd.DataFrame) -> None:
    with gzip.GzipFile(filename=str(path), mode="wb", mtime=0) as stream:
        stream.write(frame.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode())


def write_table(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False, float_format="%.17g", lineterminator="\n")


def load_inputs(config: dict):
    source_path = ROOT / config["data"]["provenance"]
    source = json.loads(source_path.read_bytes())
    inputs = {"daily_provenance": dict(path=source_path.relative_to(ROOT).as_posix(), sha256=sha(source_path.read_bytes()))}
    returns = {}
    for weighting in ("value", "equal"):
        path = ROOT / config["data"][f"{weighting}_returns"]
        raw = path.read_bytes()
        if sha(raw) != source["panels"][weighting]["sha256"]:
            raise ValueError(f"Changed archived daily source: {weighting}")
        inputs[weighting] = dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(raw), bytes=len(raw))
        returns[weighting] = load_daily_returns(path, units="decimal")
    archive = ROOT / config["part_a"]["source_directory"]
    original_manifest = json.loads((archive / "artifact_manifest.json").read_bytes())
    for item in original_manifest["files"]:
        if sha((ROOT / item["path"]).read_bytes()) != item["sha256"]:
            raise ValueError(f"Changed Experiment 1 artifact: {item['path']}")
    inputs["experiment_1_final"] = dict(path=(archive / "final/predictions.csv.gz").relative_to(ROOT).as_posix(),
                                        sha256=sha((archive / "final/predictions.csv.gz").read_bytes()))
    calendar = config["part_b"]["calendar"]
    prep_config = dict(design=config["design"], data=config["data"], calendar=dict(
        origin_start=calendar["origin_start"], response_end=calendar["new_final_response_end"],
        final_response_start=calendar["new_final_response_start"]))
    datasets, report = prepare_panels(returns, prep_config)
    return inputs, datasets, report


def validate_config(config: dict) -> None:
    plan = tomllib.loads((ROOT / config["execution"]["source_plan"]).read_text(encoding="utf-8"))
    scientific = lambda value: {key: item for key, item in value.items() if key not in {"plan", "execution"}}
    if scientific(config) != scientific(plan):
        raise ValueError("Executable settings must preserve every declared scientific planning choice")
    if not config["plan"]["executable"] or tuple(config["design"]["targets"]) != S:
        raise ValueError("An executable fixed-S6 configuration is required")


def progress(record: dict) -> None:
    print(json.dumps(dict(event="refit_complete", **record), default=str), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment_02.toml")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stage", required=True, choices=("freeze", "part-a", "development", "final", "inference", "report"))
    args = parser.parse_args()
    config_bytes = args.config.read_bytes()
    config = tomllib.loads(config_bytes.decode())
    validate_config(config)
    output = args.output.resolve()
    current = fingerprint(config_bytes)
    if args.stage == "freeze":
        if output.exists():
            parser.error("Output already exists; use a new experiment directory")
        inputs, datasets, calendar = load_inputs(config)
        if not (ROOT / ".venv/experiment_02_validation.txt").is_file():
            parser.error("Run and record the validation suite before freezing")
        if not (ROOT / ".venv/bootstrap_synthetic_validation.json").is_file():
            parser.error("Record the bounded synthetic diagnostics, including unfavorable findings, before freezing")
        output.mkdir(parents=True, exist_ok=False)
        (output / "config.toml").write_bytes(config_bytes)
        for source, destination in (("configs/experiment_02_plan.toml", "planning_config.toml"),
                                    ("experiments/02-bootstrap-history/protocol.md", "protocol.md"),
                                    ("docs/experiment_02_validation.md", "preflight.md"),
                                    (".venv/experiment_02_validation.txt", "validation.txt"),
                                    (".venv/bootstrap_synthetic_validation.json", "synthetic_validation.json")):
            shutil.copyfile(ROOT / source, output / destination)
        for path in output.iterdir():
            if path.is_file() and path.suffix in {".csv", ".json", ".md", ".toml", ".txt"}:
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        json_write(output / "calendar.json", calendar)
        json_write(output / "policies.json", policies(config))
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
        json_write(output / "protocol_freeze.json", dict(frozen_at_utc=utc(), fingerprint=current, inputs=inputs,
                   implementation_commit=commit, primary_policy=config["design"]["primary_factor_policy_all_histories"],
                   synthetic_diagnostics_sha256=sha((output / "synthetic_validation.json").read_bytes()),
                   finite_sample_calibration_established=False,
                   no_new_final_scores_computed=True, no_new_global_selection=True,
                   uninspected_evidence="Preflight found no 2025-2026 scores in this repository or available Git history; unsaved/external inspection cannot be ruled out.",
                   declared_histories=["104", "260", "520", "expanding"], part_a_family=4, part_b_family=19))
        json_write(output / "metadata.json", dict(started_at_utc=utc(), python=sys.version,
                   platform=platform.platform(), fingerprint=current, inputs=inputs, implementation_commit=commit,
                   loss="held-out target squared log-variance errors", bootstrap="joint stationary-date bootstrap; no model refitting in draws"))
        print("Protocol/configuration/data frozen before empirical execution.", flush=True)
        return

    frozen = json.loads((output / "protocol_freeze.json").read_bytes())
    if frozen["fingerprint"] != current:
        parser.error("Code, protocol, dependencies, or configuration changed after initial freeze")
    inputs, datasets, _ = load_inputs(config)
    if inputs != frozen["inputs"]:
        parser.error("Source data or Experiment 1 predictions changed after freeze")
    if args.stage in {"final", "inference", "report"}:
        development = json.loads((output / "final_freeze.json").read_bytes())
        dev_manifest = check_manifest(output / "development")
        if development["development_files"] != dev_manifest["files"]:
            parser.error("Development record changed after final freeze")

    if args.stage in {"part-a", "inference"}:
        part = "A" if args.stage == "part-a" else "B"
        directory = output / ("part_a" if part == "A" else "part_b")
        directory.mkdir(exist_ok=False)
        json_write(directory / "started.json", dict(started_at_utc=utc(), part=part))
        if part == "A":
            forecasts = pd.read_csv(ROOT / inputs["experiment_1_final"]["path"])
        else:
            check_manifest(output / "final")
            forecasts = pd.read_csv(output / "final/predictions.csv.gz")
        results, index_manifest = run_inference(forecasts, part=part, config=config, output=directory)
        write_table(directory / "bootstrap_results.csv", results)
        json_write(directory / "index_manifest.json", index_manifest)
        finish_stage(directory)
        print(json.dumps(dict(event="inference_complete", part=part, rows=len(results), time_utc=utc())), flush=True)
        return

    if args.stage == "report":
        check_manifest(output / "part_a")
        check_manifest(output / "part_b")
        check_manifest(output / "final")
        dev = pd.read_csv(output / "development/predictions.csv.gz")
        final = pd.read_csv(output / "final/predictions.csv.gz")
        a = pd.read_csv(output / "part_a/bootstrap_results.csv")
        b = pd.read_csv(output / "part_b/bootstrap_results.csv")
        write_reports(dev, final, a, b, output / "reports")
        print("Saved complete tables and figures.", flush=True)
        return

    directory = output / args.stage
    directory.mkdir(exist_ok=False)
    json_write(directory / "started.json", dict(started_at_utc=utc(), stage=args.stage))
    predictions, tuning, timing = run_stage(datasets, config, stage=args.stage, progress=progress)
    write_predictions(directory / "predictions.csv.gz", predictions)
    with gzip.GzipFile(filename=str(directory / "tuning.jsonl.gz"), mode="wb", mtime=0) as stream:
        for record in tuning:
            stream.write((json.dumps(record, sort_keys=True, default=str) + "\n").encode())
    target, aggregate = summarize_history(predictions)
    write_table(directory / "target_summary.csv", target)
    write_table(directory / "aggregate_summary.csv", aggregate)
    json_write(directory / "timing.json", timing)
    finish_stage(directory)
    if args.stage == "development":
        json_write(output / "final_freeze.json", dict(frozen_at_utc=utc(), fingerprint=current,
                   development_files=check_manifest(directory)["files"], no_new_final_scores_computed=True,
                   primary_policy=frozen["primary_policy"], final_selection_permitted=False))
    print(json.dumps(dict(event="stage_complete", stage=args.stage, timing=timing, time_utc=utc())), flush=True)


if __name__ == "__main__":
    main()
