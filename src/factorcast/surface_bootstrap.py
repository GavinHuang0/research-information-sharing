"""Joint saved-loss intervals and fixed anchors for Experiment 3.

This module never fits forecasts or selects a surface cell.  Its approximate,
marginal loss-process intervals do not establish finite-sample calibration of
the forecasting pipeline.  A history-sized BLAS batch avoids constructing a
draw x date x cell x target tensor or caching every cell's bootstrap means.
"""

from __future__ import annotations

import hashlib
import json
from numbers import Integral, Real
from pathlib import Path

import numpy as np
import pandas as pd

from .bootstrap import TARGETS, holm_adjust, stationary_indices


FINITE_HISTORIES = tuple(str(value) for value in range(52, 521, 26))
HISTORIES = (*FINITE_HISTORIES, "expanding")
SHARING_RULES = ("separate", "common", "partial")
ANCHOR_HISTORIES = frozenset(("104", "260", "520"))
CELL_COUNT = 956
COMPARISON_COUNT = 2016


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _history_label(value):
    if value == "expanding":
        return value
    if isinstance(value, bool):
        raise ValueError("Invalid history label")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid history label: {value!r}") from None
    if not np.isfinite(number) or number != int(number) or str(int(number)) not in FINITE_HISTORIES:
        raise ValueError(f"Invalid history label: {value!r}")
    return str(int(number))


def _checked_cells(cells):
    required = {"cell_index", "cell_id", "mode", "history", "sharing", "K"}
    if not isinstance(cells, pd.DataFrame) or not required.issubset(cells.columns):
        raise ValueError(f"cells requires columns {sorted(required)}")
    frame = cells.copy()
    if len(frame) != CELL_COUNT or frame[list(required)].isna().any().any():
        raise ValueError("cells must contain exactly 956 nonmissing canonical cells")
    for column in ("cell_index", "K"):
        values = frame[column].to_numpy()
        if any(isinstance(value, (bool, np.bool_)) for value in values):
            raise ValueError(f"{column} must be integer-valued")
        numeric = pd.to_numeric(frame[column], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(numeric).all() or (numeric != np.floor(numeric)).any():
            raise ValueError(f"{column} must be integer-valued")
        frame[column] = numeric.astype(np.int64)
    frame = frame.sort_values("cell_index").reset_index(drop=True)
    if not np.array_equal(frame.cell_index, np.arange(CELL_COUNT)):
        raise ValueError("cell_index must uniquely cover 0..955 and match the loss-array axis")
    if not frame.cell_id.map(lambda value: isinstance(value, str) and bool(value.strip())).all() or frame.cell_id.duplicated().any():
        raise ValueError("cell_id must be unique nonempty strings")
    frame["history"] = frame.history.map(_history_label)
    keys = ["mode", "history", "sharing", "K"]
    expected = {("none", history, "own", 0) for history in HISTORIES}
    expected.update((mode, history, sharing, k) for mode in ("matched", "expanding")
                    for history in FINITE_HISTORIES for k in range(1, 9) for sharing in SHARING_RULES)
    expected.update(("shared", "expanding", sharing, k) for k in range(1, 9) for sharing in SHARING_RULES)
    actual = set(frame[keys].itertuples(index=False, name=None))
    if frame.duplicated(keys).any() or actual != expected:
        raise ValueError("cells must exactly match the declared 936 factor and 20 own-history identities")
    # Optional redundant inventory fields must agree with the semantic identity.
    expected_columns = {
        "n_factors": frame.K.to_numpy(),
        "n_measurements": np.where(frame.sharing == "own", 0, 48),
        "n_outcomes": np.where(frame.sharing.isin(("common", "partial")), 48, 1),
    }
    for column, expected_values in expected_columns.items():
        if column in frame and not np.array_equal(pd.to_numeric(frame[column], errors="raise"), expected_values):
            raise ValueError(f"{column} disagrees with the canonical cell identity")
    return frame


def _checked_dates(dates, period):
    if period not in ("earlier_seen", "later_seen"):
        raise ValueError("period must be earlier_seen or later_seen")
    if isinstance(dates, pd.DataFrame):
        if "response_date" not in dates:
            raise ValueError("dates DataFrame requires response_date")
        response = pd.DatetimeIndex(pd.to_datetime(dates.response_date, errors="raise"))
        origin = (pd.DatetimeIndex(pd.to_datetime(dates.origin_date, errors="raise"))
                  if "origin_date" in dates else response - pd.Timedelta(days=7))
    else:
        response = pd.DatetimeIndex(pd.to_datetime(dates, errors="raise"))
        origin = response - pd.Timedelta(days=7)
    if (not len(response) or response.hasnans or origin.hasnans or response.tz is not None
            or origin.tz is not None or response.has_duplicates or not response.is_monotonic_increasing
            or not (response.dayofweek == 4).all() or not (response == response.normalize()).all()
            or not ((response - origin) == pd.Timedelta(days=7)).all()):
        raise ValueError("dates must be unique increasing timezone-free Friday labels with responses seven days after origins")
    if period == "earlier_seen":
        inside = (response >= pd.Timestamp("2011-04-01")) & (response <= pd.Timestamp("2024-12-31"))
    else:
        inside = (response >= pd.Timestamp("2025-01-03")) & (response <= pd.Timestamp("2026-08-28"))
    if not inside.all():
        raise ValueError(f"Response dates fall outside {period}")
    return origin.strftime("%Y-%m-%d").tolist(), response.strftime("%Y-%m-%d").tolist()


def _checked_losses(losses, n_dates):
    if not isinstance(losses, dict) or set(losses) != {"value", "equal"}:
        raise ValueError("losses must contain exactly value and equal weightings")
    result = {}
    for weighting in ("value", "equal"):
        values = np.asarray(losses[weighting], dtype=np.float64)
        if values.shape != (n_dates, CELL_COUNT, len(TARGETS)):
            raise ValueError(f"{weighting} losses must have shape ({n_dates},956,6)")
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"{weighting} losses must be finite and nonnegative")
        result[weighting] = values
    return result


def index_fingerprint(indices):
    """Canonical hash used by the earlier experiment's index archives."""
    digest = hashlib.sha256()
    digest.update(np.asarray(indices.shape, dtype="<i8").tobytes(order="C"))
    digest.update(np.asarray(indices, dtype="<i8", order="C").tobytes(order="C"))
    return digest.hexdigest()


def _array_fingerprint(values):
    digest = hashlib.sha256()
    digest.update(np.asarray(values.shape, dtype="<i8").tobytes())
    # Stream by date instead of materializing another full loss tensor.
    for row in values:
        digest.update(np.asarray(row, dtype="<f8", order="C").tobytes(order="C"))
    return digest.hexdigest()


def _index_counts(indices):
    counts = np.empty(indices.shape, dtype=np.float64)
    for draw, row in enumerate(indices):
        counts[draw] = np.bincount(row, minlength=indices.shape[1])
    return counts


def _means_for_history(losses, positions, counts):
    selected = losses[:, positions, :]
    with np.errstate(over="ignore", invalid="ignore"):
        observed = selected.mean(axis=0)
        sampled = (counts @ selected.reshape(len(selected), -1) / len(selected)).reshape(len(counts), len(positions), len(TARGETS))
    if not np.isfinite(observed).all() or not np.isfinite(sampled).all():
        raise ValueError("Original or resampled loss mean is nonfinite; analysis aborted")
    return observed, sampled


def _statistics(candidate, reference, denominator, sampled_candidate, sampled_reference,
                sampled_denominator, own_gain, anchor):
    if (denominator <= 0).any() or not np.isfinite(denominator).all():
        raise ValueError("Original own-history denominator MSE is zero/nonfinite; analysis aborted")
    invalid = (sampled_denominator <= 0) | ~np.isfinite(sampled_denominator)
    if invalid.any():
        draw, target = np.argwhere(invalid)[0]
        raise ValueError(f"Resampled own-history denominator MSE is zero/nonfinite at draw {draw}, target {TARGETS[target]}; analysis aborted")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if own_gain:
            effect = float(1 - np.mean(candidate / denominator))
            bootstrap = 1 - np.mean(sampled_candidate / sampled_denominator, axis=1)
        else:
            effect = float(np.mean((reference - candidate) / denominator))
            bootstrap = np.mean((sampled_reference - sampled_candidate) / sampled_denominator, axis=1)
    if not np.isfinite(effect) or not np.isfinite(bootstrap).all():
        raise ValueError("Original or resampled statistic is nonfinite; analysis aborted")
    quantiles = np.quantile(bootstrap, [0.025, 0.975], method="linear")
    tail_count = int(np.count_nonzero(bootstrap - effect >= effect)) if anchor else np.nan
    return {
        "effect": effect, "ci_low": float(2 * effect - quantiles[1]),
        "ci_high": float(2 * effect - quantiles[0]),
        "p_value": (1 + tail_count) / (len(bootstrap) + 1) if anchor else np.nan,
        "tail_count": tail_count, "p_adjusted": np.nan,
        "bootstrap_min": float(bootstrap.min()), "bootstrap_max": float(bootstrap.max()),
        "bootstrap_degenerate": bool(np.ptp(bootstrap) == 0),
    }


def _history_comparisons(group, period):
    lookup = {(row.mode, row.sharing, row.K): row for row in group.itertuples(index=False)}
    history = group.history.iloc[0]
    own = lookup[("none", "own", 0)]
    factors = group[group.sharing != "own"]
    for row in factors.itertuples(index=False):
        anchor = period == "later_seen" and row.K == 2 and (history in ANCHOR_HISTORIES or history == "expanding")
        yield "own_gain", row, own, own, anchor
    if history != "expanding":
        for k in range(1, 9):
            for sharing in SHARING_RULES:
                yield ("mode_difference", lookup[("expanding", sharing, k)], lookup[("matched", sharing, k)], own,
                       period == "later_seen" and k == 2 and history in ANCHOR_HISTORIES)
    modes = ("shared",) if history == "expanding" else ("matched", "expanding")
    for mode in modes:
        for k in range(1, 9):
            for sharing in ("common", "partial"):
                yield "pooling_difference", lookup[(mode, sharing, k)], lookup[(mode, "separate", k)], own, False


def run_inference(losses: dict[str, np.ndarray], cells: pd.DataFrame, dates, config=None,
                  period="later_seen", output: Path | None = None):
    """Return 2016 comparisons per weighting/block and joint index metadata.

    ``losses`` has axes (ordered response dates, canonical cell_index, TARGETS).
    Callers must verify squared losses against predictions/actuals and the S6
    target-axis order before calling this loss-only interface.  ``dates`` is a
    response-date sequence or a DataFrame with response_date and optional
    origin_date.  Small explicit bootstrap settings support synthetic tests;
    the empirical orchestrator must freeze the protocol's 9999/20261102/13,6,26.
    """
    config = {} if config is None else config
    if tuple(config.get("design", {}).get("targets", TARGETS)) != TARGETS:
        raise ValueError("Target order must equal the fixed S6")
    settings = config.get("bootstrap", {})
    replicates = _positive_integer(settings.get("replicates", 9999), "replicates")
    seed = settings.get("seed", 20261102)
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    primary_block = settings.get("expected_block_length_dates", 13)
    blocks = [primary_block, *settings.get("sensitivity_block_lengths_dates", [6, 26])]
    if (any(isinstance(block, bool) or not isinstance(block, Real) or not np.isfinite(block) or block < 1 for block in blocks)
            or len(set(blocks)) != len(blocks)):
        raise ValueError("Block lengths must be distinct finite numbers at least one")
    alpha = config.get("anchors", {}).get("alpha", 0.05)
    if isinstance(alpha, bool) or not isinstance(alpha, Real) or not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0,1)")
    cells = _checked_cells(cells)
    origins, responses = _checked_dates(dates, period)
    checked = _checked_losses(losses, len(responses))
    if output is not None:
        output = Path(output)
        paths = [output / name for name in ("bootstrap_results.csv", "anchor_table.csv", "bootstrap_index_manifest.json")]
        paths += [output / f"indices_b{block}.npz" for block in blocks]
        if any(path.exists() for path in paths):
            raise FileExistsError("Inference outputs already exist; use a new directory")
        output.mkdir(parents=True, exist_ok=True)
    identity = cells[["cell_index", "cell_id", "mode", "history", "sharing", "K"]].to_dict("records")
    manifest = {
        "experiment": "03-pca-history-surface", "period": period, "replicates": replicates,
        "seed": int(seed), "rng": "numpy.Generator(PCG64)", "target_order": list(TARGETS),
        "n_dates": len(responses), "n_targets": len(TARGETS), "n_cells": CELL_COUNT,
        "origin_dates": origins, "response_dates": responses,
        "canonical_cells": identity,
        "canonical_cells_sha256": hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "loss_array_hash_format": "sha256(shape_as_little_endian_int64_then_C_order_little_endian_float64_data)",
        "loss_array_sha256": {key: _array_fingerprint(value) for key, value in checked.items()},
        "index_hash_format": "sha256(shape_as_little_endian_int64_then_C_order_little_endian_int64_data)",
        "one_shared_matrix_across_weightings_targets_all_cells_contrasts": True,
        "reset_seed_per_period_block_setting": True, "models_refitted": False,
        "comparison_counts_per_weighting_block": {"own_gain": 936, "mode_difference": 456, "pooling_difference": 624},
        "anchor_family_size": 30 if period == "later_seen" else 0,
        "alpha": float(alpha),
        "rejection_rule": "effect>0 and Holm-adjusted p strictly less than alpha",
        "pvalue_rule": "(1+count(T_b-T_hat>=T_hat))/(B+1), anchors only, including ties",
        "interval_rule": "basic marginal 95%, linear quantiles, no clipping",
        "maximum_cells_per_loss_mean_batch": 49,
        "evidence_status": "approximate_exploratory_seen_period_not_calibration_validated",
        "matrices": {},
    }
    rows = []
    for block in blocks:
        indices = stationary_indices(len(responses), replicates, block, int(seed))
        fingerprint = index_fingerprint(indices)
        entry = {"block_length": block, "shape": list(indices.shape), "dtype": "<i8",
                 "sha256": fingerprint, "is_primary_block": block == primary_block}
        if output is not None:
            entry["file"] = f"indices_b{block}.npz"
            np.savez_compressed(output / entry["file"], indices=np.asarray(indices, dtype="<i8", order="C"))
            entry["file_sha256"] = hashlib.sha256((output / entry["file"]).read_bytes()).hexdigest()
        manifest["matrices"][str(block)] = entry
        counts = _index_counts(indices)
        del indices
        for weighting in ("value", "equal"):
            family_rows = []
            for history in HISTORIES:
                group = cells[cells.history == history]
                positions = group.cell_index.to_numpy()
                local = {int(position): i for i, position in enumerate(positions)}
                observed, sampled = _means_for_history(checked[weighting], positions, counts)
                for kind, candidate, reference, denominator, anchor in _history_comparisons(group, period):
                    c, r, d = (local[row.cell_index] for row in (candidate, reference, denominator))
                    result = _statistics(observed[c], observed[r], observed[d], sampled[:, c], sampled[:, r],
                                         sampled[:, d], kind == "own_gain", anchor)
                    result.update({
                        "period": period, "weighting": weighting, "kind": kind,
                        "comparison_id": f"{kind}::{candidate.cell_id}::vs::{reference.cell_id}",
                        "candidate_cell_id": candidate.cell_id, "reference_cell_id": reference.cell_id,
                        "denominator_cell_id": denominator.cell_id,
                        "candidate_mode": candidate.mode, "reference_mode": reference.mode,
                        "candidate_sharing": candidate.sharing, "reference_sharing": reference.sharing,
                        "mode": "expanding-minus-matched" if kind == "mode_difference" else candidate.mode,
                        "history": history, "sharing": candidate.sharing, "K": int(candidate.K),
                        "anchor": anchor, "family_id": f"{period}_{weighting}_b{block}_anchors30" if anchor else "",
                        "family_size": 30 if anchor else 0, "reject_adjusted": np.nan,
                        "block_length": block, "is_primary_block": block == primary_block,
                        "is_primary_weighting": weighting == "value",
                        "is_primary": weighting == "value" and block == primary_block,
                        "replicates": replicates, "n_dates": len(responses), "n_targets": len(TARGETS),
                        "index_sha256": fingerprint,
                        "evidence_status": manifest["evidence_status"],
                    })
                    for column in ("effect", "ci_low", "ci_high"):
                        result[column + "_pct"] = 100 * result[column]
                    rows.append(result)
                    if anchor:
                        family_rows.append(result)
                del observed, sampled
            expected_anchors = 30 if period == "later_seen" else 0
            if len(family_rows) != expected_anchors:
                raise RuntimeError("Anchor family cardinality disagrees with the frozen protocol")
            if family_rows:
                adjusted = holm_adjust([row["p_value"] for row in family_rows])
                for row, pvalue in zip(family_rows, adjusted):
                    row["p_adjusted"] = float(pvalue)
                    row["reject_adjusted"] = bool(row["effect"] > 0 and pvalue < alpha)
        del counts
    results = pd.DataFrame(rows)
    if len(results) != COMPARISON_COUNT * 2 * len(blocks):
        raise RuntimeError("Unexpected surface comparison cardinality")
    if output is not None:
        results.to_csv(output / "bootstrap_results.csv", index=False, float_format="%.17g", lineterminator="\n")
        results[results.anchor].to_csv(output / "anchor_table.csv", index=False, float_format="%.17g", lineterminator="\n")
        (output / "bootstrap_index_manifest.json").write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    return results, manifest
