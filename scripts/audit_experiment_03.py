"""Independent saved-output checks for Experiment 3; no model selection.

The forecast audit uses daily-derived outcomes, raw streamed records, and the
original Experiment 2 overlap. The inference audit calculates the declared
statistics directly from saved predictions and independently rebuilt indices.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("Food", "Mach", "Banks", "Oil", "Util", "Hlth")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True, default=str) + "\n").encode())


def check_files(directory):
    manifest = json.loads((directory / "stage_manifest.json").read_bytes())
    for name, expected in manifest["files"].items():
        expected = expected["sha256"] if isinstance(expected, dict) else expected
        assert sha((directory / name).read_bytes()) == expected, name
        assert (directory / name).stat().st_size < 100_000_000, name
    return manifest


def _assert_close(actual, expected, message, rtol=2e-11, atol=2e-12):
    np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol, err_msg=message)


def _inventory(path):
    cells = pd.read_csv(path, keep_default_na=False, dtype={"history": str})
    assert len(cells) == 956 and np.array_equal(cells.cell_index, np.arange(956))
    assert cells.cell_id.is_unique
    finite = tuple(str(x) for x in range(52, 521, 26))
    expected = {("none", h, "own", 0) for h in (*finite, "expanding")}
    expected |= {(m, h, s, k) for m in ("matched", "expanding") for h in finite
                 for s in ("separate", "common", "partial") for k in range(1, 9)}
    expected |= {("shared", "expanding", s, k) for s in ("separate", "common", "partial") for k in range(1, 9)}
    assert set(cells[["mode", "history", "sharing", "K"]].itertuples(index=False, name=None)) == expected
    assert np.array_equal(cells.n_factors, cells.K)
    assert np.array_equal(cells.n_measurements, np.where(cells.sharing == "own", 0, 48))
    assert np.array_equal(cells.n_outcomes, np.where(cells.sharing.isin(["common", "partial"]), 48, 1))
    return cells


def _windows(chunk, cells, inner=False):
    index = chunk.cell_index.to_numpy(dtype=int)
    cut = chunk.refit_index.to_numpy(dtype=int)
    histories = cells.history.to_numpy()[index]
    lengths = np.array([0 if h == "expanding" else int(h) for h in histories])
    outer_start = np.where(histories == "expanding", 0, cut - lengths)
    inner_stop = cut - 52
    inner_start = np.where(histories == "expanding", 0, inner_stop - lengths)
    own = cells.sharing.to_numpy()[index] == "own"
    matched = cells["mode"].to_numpy()[index] == "matched"
    if inner:
        for column, expected in (("inner_coef_start", inner_start), ("inner_coef_stop", inner_stop),
                                 ("outer_coef_start", outer_start), ("outer_coef_stop", cut)):
            assert np.array_equal(chunk[column], expected), column
        for prefix, start, stop in (("inner", inner_start, inner_stop), ("outer", outer_start, cut)):
            actual_start, actual_stop = chunk[f"{prefix}_pca_start"], chunk[f"{prefix}_pca_stop"]
            assert np.array_equal(actual_start[~own], np.where(matched, start, 0)[~own])
            assert np.array_equal(actual_stop[~own], stop[~own])
            assert actual_start[own].isna().all() and actual_stop[own].isna().all()
        assert np.array_equal(chunk.computed_components, np.where(own, 0, 8))
        assert np.array_equal(chunk.used_components, cells.K.to_numpy()[index])
    else:
        assert np.array_equal(chunk.coefficient_train_start, outer_start)
        assert np.array_equal(chunk.coefficient_train_stop, cut)
        assert np.array_equal(chunk.pca_train_start[~own], np.where(matched, outer_start, 0)[~own])
        assert np.array_equal(chunk.pca_train_stop[~own], cut[~own])
        assert chunk.pca_train_start[own].isna().all() and chunk.pca_train_stop[own].isna().all()


def audit_stage(run, period, config, datasets):
    stage = run / period
    check_files(stage)
    cells = _inventory(stage / "cells.csv")
    dates = json.loads((stage / "dates.json").read_bytes())
    assert dates["target_order"] == list(TARGETS) and dates["stage"] == period
    n = 718 if period == "earlier_seen" else 87
    assert dates["n_dates"] == n
    indices = np.asarray(dates["origin_indices"], dtype=int)
    assert np.array_equal(indices, np.arange(572, 1290) if period == "earlier_seen" else np.arange(1290, 1377))
    cutoffs = 572 + ((indices - 572) // 13) * 13
    assert np.array_equal(cutoffs, dates["refit_indices"])
    anchors = np.unique(cutoffs)
    anchor_position = {int(a): i for i, a in enumerate(anchors)}
    targets = {name: i for i, name in enumerate(TARGETS)}
    selected = np.full((2, len(anchors), 956, 6), np.nan)
    validation = np.full((2, len(anchors), 956, 6, 5), np.inf)
    chosen_count = np.zeros(selected.shape, dtype=np.uint8)
    candidate_count = np.zeros(validation.shape, dtype=np.uint8)
    raw_coverage = np.zeros((2, n, 956, 6), dtype=np.uint8)
    predictions, actuals = {}, {}
    for wi, weighting in enumerate(("value", "equal")):
        dataset = datasets[weighting]
        assert dataset.origin_dates[indices].strftime("%Y-%m-%d").tolist() == dates["origin_dates"]
        assert dataset.response_dates[indices].strftime("%Y-%m-%d").tolist() == dates["response_dates"]
        predictions[weighting] = np.load(stage / f"predictions_{weighting}.npy", mmap_mode="r")
        actuals[weighting] = np.load(stage / f"actual_{weighting}.npy", mmap_mode="r")
        assert predictions[weighting].shape == (n, 956, 6)
        assert actuals[weighting].shape == (n, 6)
        target_columns = [dataset.asset_names.index(name) for name in TARGETS]
        _assert_close(actuals[weighting], dataset.Y[indices][:, target_columns], "Daily-derived realized outcomes")
        for start in range(0, 956, 32):
            assert np.isfinite(predictions[weighting][:, start:start + 32]).all()
    prediction_rows = 0
    raw_files = sorted((stage / "predictions").rglob("*.csv.gz"))
    assert raw_files
    for path in raw_files:
        assert path.stat().st_size < 83_886_080
        for chunk in pd.read_csv(path, chunksize=25000, float_precision="round_trip", dtype={"history": str}):
            assert chunk.weighting.nunique() == 1 and set(chunk.stage) == {period}
            weighting = chunk.weighting.iloc[0]
            wi = ("value", "equal").index(weighting)
            di = chunk.date_index.to_numpy(dtype=int)
            ci = chunk.cell_index.to_numpy(dtype=int)
            ti = chunk.target_index.to_numpy(dtype=int)
            assert (di >= 0).all() and (di < n).all() and (ci >= 0).all() and (ci < 956).all()
            assert (ti >= 0).all() and (ti < 6).all()
            assert np.array_equal(chunk.origin_date, np.asarray(dates["origin_dates"])[di])
            assert np.array_equal(chunk.response_date, np.asarray(dates["response_dates"])[di])
            np.add.at(raw_coverage, (wi, di, ci, ti), 1)
            assert np.array_equal(chunk.target.to_numpy(), np.asarray(TARGETS)[ti])
            assert np.array_equal(chunk.cell_id.to_numpy(), cells.cell_id.to_numpy()[ci])
            assert np.array_equal(chunk.origin_index.to_numpy(), indices[di])
            assert np.array_equal(chunk.refit_index.to_numpy(), cutoffs[di])
            for column in ("mode", "history", "sharing", "K"):
                assert np.array_equal(chunk[column].to_numpy(), cells[column].to_numpy()[ci]), column
            _assert_close(chunk.prediction, predictions[weighting][di, ci, ti], "CSV/NPY prediction agreement")
            _assert_close(chunk.actual, actuals[weighting][di, ti], "CSV/NPY actual agreement")
            error = chunk.prediction.to_numpy() - chunk.actual.to_numpy()
            _assert_close(chunk.squared_error, error ** 2, "Raw squared losses")
            _assert_close(chunk.absolute_error, np.abs(error), "Raw absolute losses")
            _windows(chunk, cells)
            ai = chunk.refit_index.map(anchor_position).to_numpy(dtype=int)
            prior = selected[wi, ai, ci, ti]
            penalties = chunk.penalty.to_numpy(dtype=float)
            assert np.all(np.isnan(prior) | (prior == penalties))
            assert chunk.groupby(["refit_index", "cell_index", "target_index"]).penalty.nunique().max() == 1
            selected[wi, ai, ci, ti] = penalties
            prediction_rows += len(chunk)
    assert prediction_rows == n * 956 * 6 * 2
    assert (raw_coverage == 1).all()
    assert np.isfinite(selected).all()
    tuning_rows = 0
    penalty_grid = config["partial_pooling"]["penalties"]
    tuning_files = sorted((stage / "tuning").rglob("*.csv.gz"))
    assert tuning_files
    for path in tuning_files:
        assert path.stat().st_size < 83_886_080
        for chunk in pd.read_csv(path, chunksize=25000, float_precision="round_trip", dtype={"history": str}):
            weighting = chunk.weighting.iloc[0]
            assert set(chunk.weighting) == {weighting} and set(chunk.stage) == {period}
            wi = ("value", "equal").index(weighting)
            ci = chunk.cell_index.to_numpy(dtype=int)
            ti = chunk.target.map(targets).to_numpy(dtype=int)
            ai = chunk.refit_index.map(anchor_position).to_numpy(dtype=int)
            for column in ("cell_id", "mode", "history", "sharing", "K"):
                assert np.array_equal(chunk[column].to_numpy(), cells[column].to_numpy()[ci]), column
            _windows(chunk, cells, inner=True)
            dataset = datasets[weighting]
            cut = chunk.refit_index.to_numpy(dtype=int)
            assert np.array_equal(chunk.refit_origin, dataset.origin_dates[cut].strftime("%Y-%m-%d"))
            assert np.array_equal(chunk.inner_coefficient_last_response, dataset.response_dates[cut - 53].strftime("%Y-%m-%d"))
            assert np.array_equal(chunk.outer_coefficient_last_response, dataset.response_dates[cut - 1].strftime("%Y-%m-%d"))
            assert np.array_equal(chunk.validation_first_origin, dataset.origin_dates[cut - 52].strftime("%Y-%m-%d"))
            assert np.array_equal(chunk.validation_last_response, dataset.response_dates[cut - 1].strftime("%Y-%m-%d"))
            candidates = chunk.candidate_penalty.to_numpy(dtype=float)
            partial = cells.sharing.to_numpy()[ci] == "partial"
            assert np.all(np.isin(candidates[partial], penalty_grid)) and np.all(candidates[~partial] == 0)
            pi = np.array([penalty_grid.index(value) if is_partial else 0 for value, is_partial in zip(candidates, partial)])
            assert np.isfinite(chunk.validation_mse).all() and (chunk.validation_mse >= 0).all()
            assert np.all(candidate_count[wi, ai, ci, ti, pi] == 0)
            assert not chunk.duplicated(["refit_index", "cell_index", "target", "candidate_penalty"]).any()
            candidate_count[wi, ai, ci, ti, pi] += 1
            validation[wi, ai, ci, ti, pi] = chunk.validation_mse
            assert chunk.chosen.dtype == bool
            chosen = chunk.chosen.to_numpy(dtype=bool)
            chosen_count[wi, ai[chosen], ci[chosen], ti[chosen]] += 1
            assert np.array_equal(chunk.chosen_penalty, selected[wi, ai, ci, ti])
            assert np.all(candidates[chosen] == selected[wi, ai[chosen], ci[chosen], ti[chosen]])
            tuning_rows += len(chunk)
    assert (chosen_count == 1).all()
    expected_candidates = np.zeros((956, 5), dtype=np.uint8)
    expected_candidates[:, 0] = 1
    expected_candidates[cells.sharing == "partial", :] = 1
    assert np.array_equal(candidate_count, np.broadcast_to(expected_candidates[None, None, :, None, :], candidate_count.shape))
    minima = validation.argmin(axis=-1)
    expected_penalty = np.where((cells.sharing == "partial").to_numpy()[None, None, :, None], np.asarray(penalty_grid)[minima], 0)
    assert np.array_equal(selected, expected_penalty)
    old_name = "development" if period == "earlier_seen" else "final"
    old = pd.read_csv(ROOT / "results/experiment-02-2026-11-01" / old_name / "predictions.csv.gz",
                      dtype={"history": str}, float_precision="round_trip")
    policies = {"factor_separate__M-all__O-target": "separate", "factor_pooled__M-all__O-all": "common",
                "factor_partial__M-all__O-all": "partial", "local_history__M-none__O-target": "own"}
    old = old[old.policy_id.isin(policies)]
    lookup = {(r.mode, r.history, r.sharing, r.K): r.cell_index for r in cells.itertuples()}
    overlap_count, max_difference = 0, 0.0
    for (weighting, history, policy, target), group in old.groupby(["weighting", "history", "policy_id", "target"]):
        sharing = policies[policy]
        mode = "none" if sharing == "own" else "shared" if history == "expanding" else "expanding"
        ci = lookup[(mode, history, sharing, 0 if sharing == "own" else 2)]
        di = np.searchsorted(indices, group.origin_index.to_numpy())
        assert np.array_equal(indices[di], group.origin_index)
        values = predictions[weighting][di, ci, targets[target]]
        _assert_close(values, group.prediction, "Experiment 2 overlapping forecasts", rtol=2e-9, atol=2e-9)
        max_difference = max(max_difference, float(np.max(np.abs(values - group.prediction.to_numpy()))))
        overlap_count += len(group)
    assert overlap_count == (137856 if period == "earlier_seen" else 16704)
    timing = json.loads((stage / "timing.json").read_bytes())
    assert timing["prediction_rows"] == prediction_rows
    assert timing["tuning_rows"] == tuning_rows == (1481088 if period == "earlier_seen" else 185136)
    assert timing["blocks"] == (112 if period == "earlier_seen" else 14)
    assert timing["pca_fits"] == (4478 if period == "earlier_seen" else 560)
    if period == "later_seen":
        assert indices[0] == 1290 and cutoffs[0] == 1287
    result = dict(status="passed", audited_at_utc=datetime.now(timezone.utc).isoformat(), period=period,
                  prediction_rows=prediction_rows, tuning_rows=tuning_rows, dates_per_cell=n,
                  distinct_factor_cells=936, own_references=20, refit_anchors=anchors.tolist(),
                  raw_forecasts_match_NPY=True, daily_derived_actuals_match=True, all_windows_and_scalers_checked=True,
                  all_partial_penalty_candidates_and_argmins_checked=True,
                  experiment_2_overlap=dict(rows=overlap_count, maximum_absolute_prediction_difference=max_difference),
                  calibration_established=False)
    write_json(run / f"audit_{period}.json", result)
    print(json.dumps(result), flush=True)


def _independent_indices(t, b, length, seed):
    generator = np.random.Generator(np.random.PCG64(seed))
    result = np.empty((b, t), dtype=np.int64)
    for draw in range(b):
        result[draw, 0] = generator.integers(t)
        for step in range(1, t):
            restart = generator.random()
            result[draw, step] = generator.integers(t) if restart < 1 / length else (result[draw, step - 1] + 1) % t
    return result


def _expected_comparisons(cells, period):
    identity = {(r.mode, r.history, r.sharing, r.K): r.cell_id for r in cells.itertuples(index=False)}
    expected = {}
    for h in (*map(str, range(52, 521, 26)), "expanding"):
        own = identity[("none", h, "own", 0)]
        modes = ("shared",) if h == "expanding" else ("matched", "expanding")
        for mode in modes:
            for rule in ("separate", "common", "partial"):
                for k in range(1, 9):
                    candidate = identity[(mode, h, rule, k)]
                    anchor = period == "later_seen" and k == 2 and h in {"104", "260", "520", "expanding"}
                    expected[("own_gain", candidate, own, own)] = anchor
            for rule in ("common", "partial"):
                for k in range(1, 9):
                    expected[("pooling_difference", identity[(mode, h, rule, k)], identity[(mode, h, "separate", k)], own)] = False
        if h != "expanding":
            for rule in ("separate", "common", "partial"):
                for k in range(1, 9):
                    anchor = period == "later_seen" and k == 2 and h in {"104", "260", "520"}
                    expected[("mode_difference", identity[("expanding", h, rule, k)], identity[("matched", h, rule, k)], own)] = anchor
    assert len(expected) == 2016
    assert sum(expected.values()) == (30 if period == "later_seen" else 0)
    return expected


def audit_inference(run, config):
    check_files(run / "inference")
    frame = pd.read_csv(run / "inference/bootstrap_results.csv", dtype={"history": str})
    assert len(frame) == 24192 and int(frame.anchor.sum()) == 180
    assert frame.loc[~frame.anchor, ["p_value", "p_adjusted", "tail_count"]].isna().all().all()
    anchor_file = pd.read_csv(run / "inference/anchor_table.csv", dtype={"history": str})
    pd.testing.assert_frame_equal(anchor_file, frame.loc[frame.anchor].reset_index(drop=True), check_dtype=False)
    checked_rows = 0
    max_error = 0.0
    for period in ("earlier_seen", "later_seen"):
        stage = run / period
        cells = _inventory(stage / "cells.csv")
        positions = cells.set_index("cell_id").cell_index.to_dict()
        expected_comparisons = _expected_comparisons(cells, period)
        n = 718 if period == "earlier_seen" else 87
        period_file = pd.read_csv(run / "inference" / period / "bootstrap_results.csv", dtype={"history": str})
        pd.testing.assert_frame_equal(period_file, frame.loc[frame.period == period].reset_index(drop=True), check_dtype=False)
        dates = json.loads((stage / "dates.json").read_bytes())
        index_manifest = json.loads((run / "inference" / period / "bootstrap_index_manifest.json").read_bytes())
        assert index_manifest["target_order"] == list(TARGETS)
        assert index_manifest["n_dates"] == n and index_manifest["replicates"] == 9999
        assert index_manifest["origin_dates"] == dates["origin_dates"]
        assert index_manifest["response_dates"] == dates["response_dates"]
        canonical = cells[["cell_index", "cell_id", "mode", "history", "sharing", "K"]].to_dict("records")
        assert index_manifest["canonical_cells"] == canonical
        assert index_manifest["canonical_cells_sha256"] == sha(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode())
        for weighting in ("value", "equal"):
            pred_source = np.load(stage / f"predictions_{weighting}.npy", mmap_mode="r")
            actual_source = np.load(stage / f"actual_{weighting}.npy", mmap_mode="r")
            digest = hashlib.sha256(np.asarray(pred_source.shape, dtype="<i8").tobytes())
            for day in range(n):
                digest.update(np.asarray(np.square(pred_source[day] - actual_source[day, None, :]), dtype="<f8", order="C").tobytes(order="C"))
            assert index_manifest["loss_array_sha256"][weighting] == digest.hexdigest()
        for block in (13, 6, 26):
            index_path = run / "inference" / period / f"indices_b{block}.npz"
            saved = np.load(index_path)["indices"]
            assert saved.shape == (9999, n) and saved.dtype == np.dtype("int64")
            rebuilt = _independent_indices(n, 9999, block, 20261102)
            assert np.array_equal(saved, rebuilt)
            index_sha = sha(np.asarray(saved.shape, dtype="<i8").tobytes() + np.asarray(saved, dtype="<i8", order="C").tobytes())
            index_entry = index_manifest["matrices"][str(block)]
            assert index_entry["sha256"] == index_sha
            assert index_entry["file_sha256"] == sha(index_path.read_bytes())
            assert index_entry["shape"] == [9999, n] and index_entry["dtype"] == "<i8"
            counts = np.stack([np.bincount(row, minlength=n) for row in rebuilt]).astype(float)
            del rebuilt, saved
            for weighting in ("value", "equal"):
                pred = np.load(stage / f"predictions_{weighting}.npy", mmap_mode="r")
                actual = np.load(stage / f"actual_{weighting}.npy", mmap_mode="r")
                selected = frame[(frame.period == period) & (frame.weighting == weighting) & (frame.block_length == block)]
                keys = ["kind", "candidate_cell_id", "reference_cell_id", "denominator_cell_id"]
                assert len(selected) == 2016 and not selected.duplicated(keys).any()
                identities = list(selected[keys].itertuples(index=False, name=None))
                assert set(identities) == set(expected_comparisons)
                assert np.array_equal(selected.anchor, [expected_comparisons[key] for key in identities])
                assert set(selected.index_sha256) == {index_sha}
                candidate_rows = cells.iloc[selected.candidate_cell_id.map(positions).to_numpy()]
                reference_rows = cells.iloc[selected.reference_cell_id.map(positions).to_numpy()]
                for column in ("history", "sharing", "K"):
                    assert np.array_equal(selected[column], candidate_rows[column]), column
                for column in ("mode", "sharing"):
                    assert np.array_equal(selected[f"candidate_{column}"], candidate_rows[column])
                    assert np.array_equal(selected[f"reference_{column}"], reference_rows[column])
                expected_mode = np.where(selected.kind == "mode_difference", "expanding-minus-matched", candidate_rows["mode"])
                assert np.array_equal(selected["mode"], expected_mode)
                assert (selected.n_dates == n).all() and (selected.n_targets == 6).all() and (selected.replicates == 9999).all()
                _assert_close(selected[["effect_pct", "ci_low_pct", "ci_high_pct"]],
                              selected[["effect", "ci_low", "ci_high"]].to_numpy() * 100, "Percentage units")
                anchors = []
                for history, rows in selected.groupby("history", sort=False):
                    group = cells[cells.history == history]
                    indices = group.cell_index.to_numpy()
                    local = {int(ci): j for j, ci in enumerate(indices)}
                    losses = np.square(pred[:, indices, :] - actual[:, None, :])
                    original = losses.mean(axis=0)
                    sampled = (counts @ losses.reshape(n, -1) / n).reshape(9999, len(indices), 6)
                    for row in rows.itertuples(index=False):
                        c, r, d = [local[positions[name]] for name in (row.candidate_cell_id, row.reference_cell_id, row.denominator_cell_id)]
                        assert (original[d] > 0).all() and (sampled[:, d] > 0).all()
                        if row.kind == "own_gain":
                            point = 1 - (original[c] / original[d]).mean()
                            draws = 1 - (sampled[:, c] / sampled[:, d]).mean(axis=1)
                        else:
                            point = ((original[r] - original[c]) / original[d]).mean()
                            draws = ((sampled[:, r] - sampled[:, c]) / sampled[:, d]).mean(axis=1)
                        q025, q975 = np.quantile(draws, [0.025, 0.975], method="linear")
                        expected = [point, 2 * point - q975, 2 * point - q025]
                        stored = [row.effect, row.ci_low, row.ci_high]
                        _assert_close(stored, expected, "Independent bootstrap effect/basic interval")
                        max_error = max(max_error, float(np.max(np.abs(np.asarray(stored) - expected))))
                        if row.anchor:
                            tail = int(np.count_nonzero(draws - point >= point))
                            assert tail == int(row.tail_count)
                            pvalue = (1 + tail) / 10000
                            _assert_close(row.p_value, pvalue, "Independent centered-root p-value")
                            anchors.append((pvalue, row.p_adjusted))
                            expected_reject = point > 0 and row.p_adjusted < 0.05
                            assert str(row.reject_adjusted) == str(expected_reject)
                        checked_rows += 1
                    del losses, original, sampled
                if period == "later_seen":
                    assert len(anchors) == 30
                    values = np.array([a[0] for a in anchors])
                    order = np.argsort(values, kind="stable")
                    adjusted = np.empty(30)
                    adjusted[order] = np.minimum(1, np.maximum.accumulate(values[order] * np.arange(30, 0, -1)))
                    _assert_close([a[1] for a in anchors], adjusted, "Independent Holm-30 adjustment")
                else:
                    assert not anchors
            del counts
        print(json.dumps(dict(event="independent_inference_audit_period_complete", period=period)), flush=True)
    assert checked_rows == 24192
    result = dict(status="passed", audited_at_utc=datetime.now(timezone.utc).isoformat(), checked_rows=checked_rows,
                  exact_index_matrices=6, exact_anchor_tail_counts=180, independent_Holm_families=6,
                  maximum_absolute_effect_or_interval_difference=max_error, calibration_established=False)
    write_json(run / "audit_inference.json", result)
    print(json.dumps(result), flush=True)


def finalize(run, config):
    for period in ("earlier_seen", "later_seen"):
        check_files(run / period)
        assert json.loads((run / f"audit_{period}.json").read_bytes())["status"] == "passed"
    check_files(run / "inference")
    check_files(run / "reports")
    assert json.loads((run / "audit_inference.json").read_bytes())["status"] == "passed"
    files = []
    for path in sorted(run.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            raw = path.read_bytes()
            assert len(raw) < 100_000_000
            files.append(dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw)))
    result = dict(schema_version=1, created_at_utc=datetime.now(timezone.utc).isoformat(),
                  scope="all run files except this manifest", files=files,
                  scientific_selection_permitted=False, all_periods_already_seen=True,
                  calibration_and_power_status="deferred_not_run")
    write_json(run / "artifact_manifest.json", result)
    print(json.dumps(dict(event="archive_finalized", files=len(files), total_bytes=sum(x["bytes"] for x in files))), flush=True)
