"""Run the fixed Experiment 4 forecast comparisons on the inherited calendar."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import gzip
import hashlib
from importlib.metadata import version
import io
import json
import os
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
import tomllib

ROOT = Path(__file__).resolve().parents[1]
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from factorcast.comparison import predict_window
from factorcast.data import load_daily_returns
from factorcast.pilot import S, prepare_panels


EXPERIMENT_03 = ROOT / "results/experiment-03-2026-11-03"
PROTOCOL = "experiments/04-panel-vs-pc-regularization/protocol.md"
METHODS = (
    "own_ols", "own_ridge", "own_elasticnet", "panel_ols", "panel_ridge",
    "pc_ols", "pc_ridge", "pc_common", "own_ridge_plus_pcs", "panel_ridge_legacy",
)
PREDICTION_COLUMNS = (
    "weighting", "period", "history", "method", "target", "origin_index",
    "origin_date", "response_date", "refit_index", "train_start", "train_stop",
    "penalty", "actual", "prediction", "squared_error",
)
TUNING_COLUMNS = (
    "weighting", "history", "method", "target", "refit_index", "inner_train_start",
    "inner_train_stop", "outer_train_start", "outer_train_stop", "penalty",
    "validation_mse", "selected",
)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprints(paths) -> dict[str, str]:
    return {
        (path.relative_to(ROOT) if path.is_relative_to(ROOT) else path).as_posix(): sha256(path)
        for path in paths
    }


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


@contextmanager
def compressed_csv(path: Path, columns):
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=5, mtime=0) as archive:
            with io.TextIOWrapper(archive, encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(columns)
                yield writer


def settings(config):
    design, calendar = config["design"], config["calendar"]
    if tuple(design["targets"]) != S or design.get("protocol", PROTOCOL) != PROTOCOL:
        raise ValueError("Experiment 4 uses the fixed target order and protocol")
    histories = design["finite_histories"]
    initial = calendar["first_outer_cutoff_pairs"]
    validation = calendar["validation_pairs"]
    refit = calendar["refit_every_pairs"]
    if (initial, validation, refit) != (572, 52, 13) or histories != [52, 104, 260, 520]:
        raise ValueError("Experiment 4 uses the declared histories and inherited refit schedule")
    penalties = {name: tuple(map(float, design[name])) for name in ("ridge", "elasticnet")}
    for grid in penalties.values():
        if (len(grid) < 2 or grid[0] != 0 or not np.isfinite(grid).all()
                or tuple(sorted(set(grid))) != grid):
            raise ValueError("Penalty grids must start at zero and increase strictly")
    penalties["elasticnet_l1_ratio"] = float(design["elasticnet_l1_ratio"])
    if penalties["elasticnet_l1_ratio"] != 0.5:
        raise ValueError("Experiment 4 uses the declared elastic-net mixture")
    return histories + [None], penalties


def load_inputs(config):
    data, calendar = config["data"], config["calendar"]
    provenance = ROOT / data["provenance"]
    source = json.loads(provenance.read_bytes())
    inputs = fingerprints([provenance])
    returns = {}
    for weighting in ("value", "equal"):
        path = ROOT / data[f"{weighting}_returns"]
        returns[weighting] = load_daily_returns(path, units="decimal")
        actual_hash = returns[weighting].attrs["source_sha256"]
        if actual_hash != source["panels"][weighting]["sha256"]:
            raise ValueError(f"Archived daily return input changed: {weighting}")
        inputs[path.relative_to(ROOT).as_posix()] = actual_hash

    prep = dict(
        design=dict(targets=list(S), small_panel=list(S)), data=data,
        calendar=dict(origin_start=calendar["origin_start"], response_end=calendar["response_end"],
                      final_response_start=calendar["later_seen_response_start"]),
    )
    datasets, report = prepare_panels(returns, prep)
    first = datasets["value"]
    for dataset in datasets.values():
        if (not dataset.origin_dates.equals(first.origin_dates)
                or not dataset.response_dates.equals(first.response_dates)
                or dataset.asset_names != first.asset_names):
            raise ValueError("The return weightings must share identical dates and industry order")
    if len(first.X) != 1377 or len(first.asset_names) != 48 or not first.origin_dates.is_unique:
        raise ValueError("The inherited complete-case industry panel changed")

    initial, refit = calendar["first_outer_cutoff_pairs"], calendar["refit_every_pairs"]
    origin_dates = first.origin_dates.strftime("%Y-%m-%d").tolist()
    response_dates = first.response_dates.strftime("%Y-%m-%d").tolist()
    period_by_row = [None] * len(first.X)
    for period in ("earlier_seen", "later_seen"):
        path = EXPERIMENT_03 / period / "dates.json"
        inputs.update(fingerprints([path]))
        archived = json.loads(path.read_bytes())
        if period == "earlier_seen":
            indices = [row for row in range(initial, len(first.X))
                       if response_dates[row] <= calendar["earlier_seen_response_end"]]
            expected_count = calendar["expected_inherited_earlier_dates"]
        else:
            indices = [row for row in range(initial, len(first.X))
                       if response_dates[row] >= calendar["later_seen_response_start"]]
            expected_count = calendar["expected_inherited_later_dates"]
        dates = dict(
            n_dates=len(indices), target_order=list(S), stage=period, origin_indices=indices,
            origin_dates=[origin_dates[row] for row in indices],
            response_dates=[response_dates[row] for row in indices],
            refit_indices=[initial + (row - initial) // refit * refit for row in indices],
        )
        if len(indices) != expected_count or any(archived[key] != value for key, value in dates.items()):
            raise ValueError(f"Forecast dates or refit anchors differ from Experiment 3: {period}")
        for row in indices:
            if period_by_row[row] is not None:
                raise ValueError("Evaluation periods overlap")
            period_by_row[row] = period
    if any(period is None for period in period_by_row[initial:]):
        raise ValueError("The declared periods omit inherited forecast dates")
    return datasets, report, inputs, period_by_row


def candidate_grids(penalties):
    ridge = penalties["ridge"]
    return dict(
        own_ols=(0.0,), own_ridge=ridge, own_elasticnet=penalties["elasticnet"],
        panel_ols=(0.0,), panel_ridge=ridge, pc_ols=(0.0,), pc_ridge=ridge,
        pc_common=(0.0,), own_ridge_plus_pcs=ridge,
        panel_ridge_legacy=tuple(value for value in ridge if value > 0),
    )


def validate_forecasts(predictions, grids, expected_shape):
    if set(predictions) != set(METHODS):
        raise ValueError("Estimator output differs from the declared method inventory")
    for method, grid in grids.items():
        for penalty in grid:
            forecast = predictions[method][penalty]
            if forecast.shape != expected_shape or not np.isfinite(forecast).all():
                raise ValueError(f"Invalid forecast array: {method}, penalty={penalty}")


def forecast(datasets, periods, config, archive):
    histories, penalties = settings(config)
    grids = candidate_grids(penalties)
    calendar = config["calendar"]
    initial, validation, refit = (calendar[key] for key in (
        "first_outer_cutoff_pairs", "validation_pairs", "refit_every_pairs",
    ))
    targets = [datasets["value"].asset_names.index(target) for target in S]
    prediction_count = tuning_count = window_count = 0
    with (
        compressed_csv(archive / "predictions.csv.gz", PREDICTION_COLUMNS) as prediction_writer,
        compressed_csv(archive / "tuning.csv.gz", TUNING_COLUMNS) as tuning_writer,
        (archive / "windows.jsonl").open("w", encoding="utf-8", newline="\n") as windows,
    ):
        for weighting, dataset in datasets.items():
            origin_dates = dataset.origin_dates.strftime("%Y-%m-%d").tolist()
            response_dates = dataset.response_dates.strftime("%Y-%m-%d").tolist()
            for ordinal, cut in enumerate(range(initial, len(dataset.X), refit), start=1):
                inner_stop = cut - validation
                if (response_dates[inner_stop - 1] > origin_dates[inner_stop]
                        or response_dates[cut - 1] > origin_dates[cut]):
                    raise ValueError("An estimation window includes an unavailable outcome")
                validation_rows = np.arange(inner_stop, cut)
                forecast_rows = np.arange(cut, min(cut + refit, len(dataset.X)))
                validation_actual = dataset.Y[validation_rows][:, targets]
                forecast_actual = dataset.Y[forecast_rows][:, targets]
                for history in histories:
                    label = "expanding" if history is None else str(history)
                    inner_start = 0 if history is None else inner_stop - history
                    outer_start = 0 if history is None else cut - history
                    inner, inner_diagnostics = predict_window(
                        dataset, inner_start, inner_stop, validation_rows, targets, penalties,
                    )
                    outer, outer_diagnostics = predict_window(
                        dataset, outer_start, cut, forecast_rows, targets, penalties,
                    )
                    validate_forecasts(inner, grids, validation_actual.shape)
                    validate_forecasts(outer, grids, forecast_actual.shape)
                    window = dict(
                        weighting=weighting, history=label, refit_index=cut,
                        inner_train_start=inner_start, inner_train_stop=inner_stop,
                        outer_train_start=outer_start, outer_train_stop=cut,
                        inner=inner_diagnostics, outer=outer_diagnostics,
                    )
                    windows.write(json.dumps(window, allow_nan=False, sort_keys=True) + "\n")
                    window_count += 1
                    chosen_penalties = {}
                    for method in METHODS:
                        grid = grids[method]
                        errors = np.array([((inner[method][penalty] - validation_actual) ** 2).mean(axis=0)
                                           for penalty in grid])
                        if not np.isfinite(errors).all():
                            raise ValueError(f"Invalid validation MSE: {weighting}, {label}, {method}, {cut}")
                        if method == "own_ridge_plus_pcs":
                            chosen = chosen_penalties["own_ridge"]
                        else:
                            # The configured grids are sorted, so argmin breaks ties by smaller penalty.
                            chosen = [grid[index] for index in np.argmin(errors, axis=0)]
                        chosen_penalties[method] = chosen
                        for target_index, target in enumerate(S):
                            penalty = chosen[target_index]
                            for candidate_index, candidate in enumerate(grid):
                                tuning_writer.writerow((weighting, label, method, target, cut,
                                                        inner_start, inner_stop, outer_start, cut, candidate,
                                                        errors[candidate_index, target_index], candidate == penalty))
                            tuning_count += len(grid)
                            prediction = outer[method][penalty][:, target_index]
                            actual = forecast_actual[:, target_index]
                            loss = (actual - prediction) ** 2
                            if not np.isfinite(loss).all():
                                raise ValueError(f"Invalid evaluation loss: {weighting}, {label}, {method}, {cut}")
                            prediction_writer.writerows(
                                (weighting, periods[row], label, method, target, row,
                                 origin_dates[row], response_dates[row], cut, outer_start, cut,
                                 penalty, realized, fitted, squared_error)
                                for row, realized, fitted, squared_error in zip(
                                    forecast_rows, actual, prediction, loss, strict=True,
                                )
                            )
                            prediction_count += len(forecast_rows)
                if ordinal % 10 == 0 or forecast_rows[-1] == len(dataset.X) - 1:
                    print(f"{weighting}: {ordinal} refits through response {response_dates[forecast_rows[-1]]}", flush=True)
    expected = sum(len(dataset.X) - initial for dataset in datasets.values()) * len(histories) * len(METHODS) * len(S)
    if prediction_count != expected:
        raise ValueError("The archive does not contain one prediction for every declared cell")
    return dict(predictions=prediction_count, tuning_candidates=tuning_count, windows=window_count)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment_04.toml")
    parser.add_argument("--output", type=Path, default=ROOT / "results/experiment-04-2026-11-23")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    config_path = args.config.resolve()
    config_bytes = config_path.read_bytes()
    config = tomllib.loads(config_bytes.decode("utf-8"))
    settings(config)
    sources = sorted((ROOT / "src/factorcast").glob("*.py"))
    sources += [Path(__file__).resolve(), ROOT / PROTOCOL, ROOT / "requirements-lock.txt", config_path]
    source_hashes = fingerprints(sources)
    started_at = datetime.now(timezone.utc).isoformat()
    started = perf_counter()
    datasets, calendar, inputs, period_by_row = load_inputs(config)
    with TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temp:
        archive = Path(temp) / "archive"
        archive.mkdir()
        (archive / "config.toml").write_bytes(config_bytes)
        write_json(archive / "calendar.json", calendar)
        counts = forecast(datasets, period_by_row, config, archive)
        if fingerprints(sources) != source_hashes or fingerprints([ROOT / key for key in inputs]) != inputs:
            raise ValueError("Source or input changed during the run")
        manifest = dict(
            experiment_id="04-panel-vs-pc-regularization", started_at_utc=started_at,
            finished_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=perf_counter() - started,
            evidence_status="descriptive_previously_inspected_periods", calibration_study="deferred",
            source_sha256=source_hashes, input_sha256=inputs, methods=list(METHODS), counts=counts,
            versions=dict(python=platform.python_version(), **{
                package: version(package) for package in ("numpy", "pandas", "scipy", "scikit-learn")
            }),
            files={path.name: sha256(path) for path in sorted(archive.iterdir())},
        )
        write_json(archive / "manifest.json", manifest)
        archive.rename(output)
    print(f"Saved {counts['predictions']:,} forecasts to {output}", flush=True)


if __name__ == "__main__":
    main()
