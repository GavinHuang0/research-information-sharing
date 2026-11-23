"""Audit Experiment 4's archived forecasts and tuning against the inherited sample."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "results/experiment-03-2026-11-03"
HISTORY_STUDY = ROOT / "results/experiment-02-2026-11-01"
DEFAULT_OUTPUT = ROOT / "results/experiment-04-2026-11-23"
TARGETS = ("Food", "Mach", "Banks", "Oil", "Util", "Hlth")
WEIGHTINGS = ("value", "equal")
PERIODS = ("earlier_seen", "later_seen")
METHODS = (
    "own_ols", "own_ridge", "own_elasticnet", "panel_ols", "panel_ridge",
    "pc_ols", "pc_ridge", "pc_common", "own_ridge_plus_pcs", "panel_ridge_legacy",
)
FORECAST_KEY = ["weighting", "history", "method", "origin_index", "target"]
TUNING_KEY = ["weighting", "history", "method", "refit_index", "target"]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def check_equal(actual, expected, label):
    np.testing.assert_array_equal(actual, expected, err_msg=label)


def check_close(actual, expected, label, *, rtol=2e-11, atol=2e-12):
    np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol, err_msg=label)
    return float(np.max(np.abs(np.asarray(actual) - np.asarray(expected)), initial=0))


def verify_files(output):
    manifest = json.loads((output / "manifest.json").read_bytes())
    archived = manifest["files"]
    for name in ("config.toml", "predictions.csv.gz", "tuning.csv.gz", "windows.jsonl"):
        check(name in archived, f"Archive manifest omits {name}")
    for base, records in ((output, archived), (ROOT, manifest["input_sha256"])):
        for name, expected in records.items():
            path = base / name
            check(path.resolve().is_relative_to(base.resolve()), f"Invalid manifest path {name}")
            with path.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            check(digest == expected, f"Fingerprint mismatch for {path}")
    return len(archived), len(manifest["input_sha256"])


def inherited_calendar(config):
    settings = config["calendar"]
    cutoff = settings["first_outer_cutoff_pairs"]
    step = settings["refit_every_pairs"]
    calendar = []
    for period in PERIODS:
        dates = json.loads((PREVIOUS / period / "dates.json").read_bytes())
        check(dates["stage"] == period, f"Inherited period label changed: {period}")
        check_equal(dates["target_order"], TARGETS, f"Inherited target order for {period}")
        origins = np.asarray(dates["origin_indices"])
        check(len(origins) == dates["n_dates"] == settings[f"expected_inherited_{period.removesuffix('_seen')}_dates"],
              f"Unexpected number of dates for {period}")
        aligned = pd.DataFrame({
            "origin_index": origins, "period": period, "origin_date": dates["origin_dates"],
            "response_date": dates["response_dates"], "refit_index": dates["refit_indices"],
        })
        response = pd.to_datetime(aligned.response_date)
        origin = pd.to_datetime(aligned.origin_date)
        check(bool(((response - origin) == pd.Timedelta(days=7)).all()), f"One-week alignment changed: {period}")
        check_equal(aligned.refit_index, cutoff + (origins - cutoff) // step * step, f"Refit schedule for {period}")
        check(response.is_monotonic_increasing and response.is_unique, f"Nonchronological dates for {period}")
        calendar.append(aligned)
    combined = pd.concat(calendar, ignore_index=True).set_index("origin_index", verify_integrity=True)
    check_equal(combined.index, np.arange(cutoff, cutoff + len(combined)), "Coverage across the period boundary")
    return combined


def training_start(stop, histories):
    length = np.array([0 if history == "expanding" else int(history) for history in histories])
    start = np.where(length == 0, 0, stop - length)
    check(bool((start >= 0).all()), "Training start precedes available history")
    return start


def verify_predictions(output, calendar, histories):
    frame = pd.read_csv(output / "predictions.csv.gz", dtype={"history": str}, float_precision="round_trip")
    expected = pd.MultiIndex.from_product(
        [WEIGHTINGS, histories, METHODS, calendar.index, TARGETS], names=FORECAST_KEY,
    )
    frame = frame.set_index(FORECAST_KEY, verify_integrity=True)
    check(len(frame) == len(expected) and frame.index.difference(expected).empty,
          "Forecast archive does not contain the declared weighting, history, method, date and target grid")
    frame = frame.reindex(expected)
    rows = calendar.loc[frame.index.get_level_values("origin_index")]
    for column in ("period", "origin_date", "response_date", "refit_index"):
        check_equal(frame[column], rows[column], f"Forecast {column}")
    cutoff = rows.refit_index.to_numpy()
    check_equal(frame.train_stop, cutoff, "Forecast training stop")
    check_equal(frame.train_start, training_start(cutoff, frame.index.get_level_values("history")), "Forecast training start")
    values = frame[["actual", "prediction", "squared_error", "penalty"]].to_numpy()
    check(bool(np.isfinite(values).all()), "Nonfinite forecast, loss, or penalty")
    check(bool((frame.penalty >= 0).all()), "Negative forecast penalty")
    error = (frame.actual - frame.prediction) ** 2
    difference = check_close(frame.squared_error, error, "Archived squared loss", rtol=3e-15, atol=1e-16)
    return frame.reset_index(), difference


def candidate_penalties(method, design):
    if method == "own_elasticnet":
        return design["elasticnet"]
    if method == "panel_ridge_legacy":
        return [penalty for penalty in design["ridge"] if penalty > 0]
    if method in {"own_ridge", "panel_ridge", "pc_ridge", "own_ridge_plus_pcs"}:
        return design["ridge"]
    return [0.0]


def verify_tuning(output, config, calendar, histories, forecasts):
    tuning = pd.read_csv(output / "tuning.csv.gz", dtype={"history": str, "selected": str}, float_precision="round_trip")
    design = config["design"]
    candidates = tuning[["penalty", "validation_mse"]].to_numpy()
    check(bool(np.isfinite(candidates).all() and (candidates >= 0).all()), "Invalid tuning candidate or validation loss")
    check(set(tuning.selected) <= {"True", "False"}, "Invalid tuning selection flag")
    check(set(tuning.method) == set(METHODS), "Unexpected tuning method inventory")
    refits = calendar.refit_index.unique()
    for method in METHODS:
        observed = pd.MultiIndex.from_frame(tuning.loc[tuning.method == method, [*TUNING_KEY, "penalty"]])
        expected = pd.MultiIndex.from_product(
            [WEIGHTINGS, histories, [method], refits, TARGETS, candidate_penalties(method, design)],
            names=[*TUNING_KEY, "penalty"],
        )
        check(len(observed) == len(expected) and observed.is_unique and observed.difference(expected).empty,
              f"Incomplete, duplicated, or unexpected tuning candidates for {method}")

    cutoff = tuning.refit_index.to_numpy()
    inner_stop = cutoff - config["calendar"]["validation_pairs"]
    check_equal(tuning.inner_train_stop, inner_stop, "Inner training stop before historical validation")
    check_equal(tuning.inner_train_start, training_start(inner_stop, tuning.history), "Inner training start")
    check_equal(tuning.outer_train_stop, cutoff, "Outer refit stop")
    check_equal(tuning.outer_train_start, training_start(cutoff, tuning.history), "Outer refit start")

    chosen = tuning[tuning.selected == "True"].set_index(TUNING_KEY, verify_integrity=True).penalty
    expected_count = len(WEIGHTINGS) * len(histories) * len(METHODS) * len(refits) * len(TARGETS)
    check(len(chosen) == expected_count, "Every forecast group must select exactly one penalty")
    independent = tuning[tuning.method != "own_ridge_plus_pcs"]
    lowest = independent.sort_values(["validation_mse", "penalty"]).drop_duplicates(TUNING_KEY).set_index(TUNING_KEY).penalty
    check_equal(chosen.reindex(lowest.index), lowest, "Minimum validation MSE and smallest-penalty tie break")
    tied = chosen.xs("own_ridge_plus_pcs", level="method")
    check_equal(tied, chosen.xs("own_ridge", level="method").reindex(tied.index), "PC addition must use the same penalty as own ridge")
    selected_for_forecast = chosen.reindex(pd.MultiIndex.from_frame(forecasts[TUNING_KEY]))
    check_equal(forecasts.penalty, selected_for_forecast, "Forecasts use the selected historical penalties")
    return len(tuning), len(chosen), len(refits)


def verify_windows(output, config, calendar, histories):
    windows = pd.read_json(output / "windows.jsonl", lines=True, dtype={"history": str})
    keys = ["weighting", "history", "refit_index"]
    expected = pd.MultiIndex.from_product([WEIGHTINGS, histories, calendar.refit_index.unique()], names=keys)
    observed = pd.MultiIndex.from_frame(windows[keys])
    check(len(observed) == len(expected) and observed.is_unique and observed.difference(expected).empty,
          "Incomplete rank and training-window diagnostics")
    result = {}
    for name in ("inner", "outer"):
        stop = windows.refit_index.to_numpy()
        if name == "inner":
            stop = stop - config["calendar"]["validation_pairs"]
        start = training_start(stop, windows.history)
        check_equal(windows[f"{name}_train_start"], start, f"Diagnostic {name} training start")
        check_equal(windows[f"{name}_train_stop"], stop, f"Diagnostic {name} training stop")
        ranks = np.array([record["panel_residual_rank"] for record in windows[name]], dtype=int)
        degrees = np.array([record["panel_residual_df"] for record in windows[name]], dtype=int)
        condition = np.array([record["panel_condition_number"] for record in windows[name]], dtype=float)
        check(ranks.shape == degrees.shape == condition.shape == (len(expected), len(TARGETS)),
              f"Missing target diagnostics in {name} windows")
        check(bool(((ranks >= 0) & (ranks <= 47) & (degrees >= 0)).all()), f"Invalid design ranks in {name} windows")
        controls_rank = (stop - start)[:, None] - ranks - degrees
        check(bool(((1 <= controls_rank) & (controls_rank <= 4)).all()), f"Invalid controls rank in {name} windows")
        check(bool((np.isfinite(condition) == (ranks == 47)).all()), f"Invalid condition numbers in {name} windows")
        check(bool((condition[np.isfinite(condition)] >= 1).all()), f"Condition number below one in {name} windows")
        result[name] = {
            history: {
                "minimum_residual_df": int(degrees[windows.history == history].min()),
                "rank_deficient_target_windows": int((ranks[windows.history == history] < 47).sum()),
                "maximum_finite_condition_number": float(
                    np.max(condition[(windows.history == history).to_numpy()[:, None] & np.isfinite(condition)], initial=1)
                ),
            }
            for history in histories
        }
    return len(windows), result


def verify_experiment_03(frame, histories):
    cells = pd.read_csv(PREVIOUS / "cells.csv", dtype={"history": str})
    lookup = cells.set_index(["mode", "history", "sharing", "K"], verify_integrity=True).cell_index
    methods = {"own_ols": "own", "pc_ols": "separate", "pc_common": "common"}
    counts = {method: 0 for method in methods}
    maximum = {method: 0.0 for method in methods}
    actual_count = 0
    for (weighting, period), part in frame.groupby(["weighting", "period"], sort=False):
        directory = PREVIOUS / period
        dates = json.loads((directory / "dates.json").read_bytes())
        origins = dates["origin_indices"]
        original_actuals = np.load(directory / f"actual_{weighting}.npy", mmap_mode="r", allow_pickle=False)
        original_forecasts = np.load(directory / f"predictions_{weighting}.npy", mmap_mode="r", allow_pickle=False)
        comparison_index = pd.MultiIndex.from_product([origins, TARGETS], names=["origin_index", "target"])
        actual = part.set_index(["origin_index", "target"]).actual
        actual_repeated = pd.Series(original_actuals.ravel(), index=comparison_index).reindex(actual.index)
        check_equal(actual, actual_repeated, f"Actual values for {weighting}/{period}")
        actual_count += len(part)
        for (history, method), selected in part[part.method.isin(methods)].groupby(["history", "method"], sort=False):
            mode = "shared" if history == "expanding" else "matched"
            key = ("none", history, "own", 0) if method == "own_ols" else (mode, history, methods[method], 2)
            expected = original_forecasts[:, int(lookup.loc[key]), :].ravel()
            observed = selected.set_index(["origin_index", "target"]).prediction.reindex(comparison_index)
            gap = check_close(observed, expected, f"Experiment 3 {weighting}/{period}/{history}/{method}")
            maximum[method] = max(maximum[method], gap)
            counts[method] += len(expected)
    check(all(value == len(histories) * len(WEIGHTINGS) * 805 * len(TARGETS) for value in counts.values()),
          "Incomplete Experiment 3 forecast cross-check")
    return actual_count, counts, maximum


def verify_legacy_ridge(frame):
    key = ["weighting", "history", "origin_index", "target"]
    columns = [*key, "penalty", "prediction", "policy_id"]
    observed = frame[(frame.method == "panel_ridge_legacy") & (frame.history != "52")].set_index(key)
    count = 0
    maximum = 0.0
    for period, subdirectory in (("earlier_seen", "development"), ("later_seen", "final")):
        source = HISTORY_STUDY / subdirectory / "predictions.csv.gz"
        archive = pd.read_csv(source, usecols=columns, dtype={"history": str}, float_precision="round_trip")
        archive = archive[archive.policy_id == "ridge__M-all__O-target"].set_index(key, verify_integrity=True)
        comparable = observed[observed.period == period]
        check(len(comparable) == len(archive) and archive.index.difference(comparable.index).empty,
              f"Different legacy ridge sample for {period}")
        archive = archive.reindex(comparable.index)
        check_equal(comparable.penalty, archive.penalty, f"Legacy ridge penalty replay for {period}")
        gap = check_close(comparable.prediction, archive.prediction, f"Legacy ridge forecast replay for {period}")
        count += len(archive)
        maximum = max(maximum, gap)
    return count, maximum


def verify_zero_penalties(frame):
    index = ["weighting", "history", "origin_index", "target"]
    checks = {}
    for method, equivalent in (
        ("own_ridge", "own_ols"), ("own_elasticnet", "own_ols"), ("panel_ridge", "panel_ols"),
        ("pc_ridge", "pc_ols"), ("own_ridge_plus_pcs", "pc_ols"),
    ):
        zero = frame[(frame.method == method) & (frame.penalty == 0)].set_index(index).prediction
        reference = frame[frame.method == equivalent].set_index(index).prediction.reindex(zero.index)
        maximum = check_close(zero, reference, f"Zero-penalty {method} nesting")
        checks[method] = {"forecast_rows": len(zero), "max_absolute_difference": maximum}
    return checks


def audit(output):
    archive_files, inputs = verify_files(output)
    config = tomllib.loads((output / "config.toml").read_text(encoding="utf-8"))
    check_equal(config["design"]["targets"], TARGETS, "Declared targets")
    histories = tuple(str(length) for length in config["design"]["finite_histories"]) + ("expanding",)
    calendar = inherited_calendar(config)
    forecasts, error_difference = verify_predictions(output, calendar, histories)
    tuning_count, choices, refits = verify_tuning(output, config, calendar, histories, forecasts)
    windows, rank_diagnostics = verify_windows(output, config, calendar, histories)
    actuals, comparison_counts, comparison_max = verify_experiment_03(forecasts, histories)
    legacy_count, legacy_max = verify_legacy_ridge(forecasts)
    return {
        "status": "passed", "archive_files_verified": archive_files, "input_hashes_verified": inputs,
        "prediction_rows": len(forecasts), "tuning_candidates": tuning_count, "selected_penalties": choices,
        "refit_anchors": refits, "actual_rows_checked": actuals, "max_absolute_squared_error_difference": error_difference,
        "windows_checked": windows, "panel_rank_diagnostics": rank_diagnostics,
        "experiment_03_forecast_rows": comparison_counts, "experiment_03_max_absolute_forecast_differences": comparison_max,
        "experiment_02_legacy_ridge_forecast_rows": legacy_count, "experiment_02_legacy_ridge_max_absolute_difference": legacy_max,
        "zero_penalty_nesting": verify_zero_penalties(forecasts),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Experiment 4 archive to verify")
    args = parser.parse_args()
    result = audit(args.output)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (args.output / "audit.json").write_bytes(text.encode())
    print(text, end="")


if __name__ == "__main__":
    main()
