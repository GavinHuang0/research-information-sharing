"""Paired stationary-bootstrap comparisons for the frozen second experiment.

The functions resample existing forecast losses; they never refit a model or
select a policy.  Their approximate loss-process inference does not establish
finite-sample calibration of the complete forecasting/selection pipeline.
"""

from __future__ import annotations

import hashlib
import json
from numbers import Integral, Real
from pathlib import Path

import numpy as np
import pandas as pd


TARGETS = ("Food", "Mach", "Banks", "Oil", "Util", "Hlth")
FACTOR_POLICY = "factor_pooled__M-all__O-all"
REFERENCE_POLICIES = (
    "local_history__M-none__O-target", "ridge__M-all__O-target",
    "elasticnet__M-all__O-target", "pls__M-all__O-target",
)
HISTORIES = ("104", "260", "520", "expanding")


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def stationary_indices(n_dates, replicates=9999, block_length=13, seed=20261031):
    """Return B x T int64 indices in the exact declared PCG64 draw order.

    Each replicate starts with an integer draw.  Each subsequent position uses
    one restart-uniform draw and an integer draw only when a restart occurs.
    The otherwise branch advances circularly; no unused integers are drawn.
    """
    n_dates = _positive_integer(n_dates, "n_dates")
    replicates = _positive_integer(replicates, "replicates")
    if (isinstance(block_length, bool) or not isinstance(block_length, Real)
            or not np.isfinite(block_length) or block_length < 1):
        raise ValueError("block_length must be finite and at least one")
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    indices = np.empty((replicates, n_dates), dtype=np.int64)
    probability = 1.0 / block_length
    for replicate in range(replicates):
        indices[replicate, 0] = rng.integers(0, n_dates)
        for position in range(1, n_dates):
            if rng.random() < probability:
                indices[replicate, position] = rng.integers(0, n_dates)
            else:
                indices[replicate, position] = (indices[replicate, position - 1] + 1) % n_dates
    return indices


def holm_adjust(pvalues):
    """Return Holm step-down adjusted values in the original comparison order."""
    values = np.asarray(pvalues, dtype=float)
    if (values.ndim != 1 or values.size == 0 or not np.isfinite(values).all()
            or ((values < 0) | (values > 1)).any()):
        raise ValueError("pvalues must be a nonempty finite vector in [0, 1]")
    order = np.argsort(values, kind="stable")
    adjusted = np.minimum(1.0, np.maximum.accumulate(values[order] * np.arange(len(values), 0, -1)))
    result = np.empty_like(adjusted)
    result[order] = adjusted
    return result


def _checked_losses(values, name):
    losses = np.asarray(values, dtype=float)
    if losses.ndim != 2 or losses.shape[0] == 0 or losses.shape[1] != len(TARGETS):
        raise ValueError(f"{name} must have shape (positive dates, 6 targets)")
    if not np.isfinite(losses).all() or (losses < 0).any():
        raise ValueError(f"{name} losses must be finite and nonnegative")
    return losses


def _checked_indices(indices, n_dates):
    indices = np.asarray(indices)
    if (indices.ndim != 2 or indices.shape[0] == 0 or indices.shape[1] != n_dates
            or not np.issubdtype(indices.dtype, np.integer)
            or (indices < 0).any() or (indices >= n_dates).any()):
        raise ValueError("indices must be a nonempty B x T integer matrix with entries in [0,T)")
    return indices


def _loss_means(losses, indices):
    # B x T x targets is deliberately constructed only for a bounded batch.
    # The returned B x targets means are small and reusable across comparisons.
    with np.errstate(over="ignore", invalid="ignore"):
        observed = losses.mean(axis=0)
        sampled = np.empty((len(indices), losses.shape[1]), dtype=float)
        for start in range(0, len(indices), 256):
            stop = min(start + 256, len(indices))
            sampled[start:stop] = losses[indices[start:stop]].mean(axis=1)
    if not np.isfinite(observed).all() or not np.isfinite(sampled).all():
        raise ValueError("Original or resampled loss mean is nonfinite; analysis aborted")
    return observed, sampled


def _comparison_statistics(candidate_means, reference_means):
    candidate, candidate_boot = candidate_means
    reference, reference_boot = reference_means
    if (reference <= 0).any() or not np.isfinite(reference).all():
        raise ValueError("Original reference denominator MSE is zero/nonfinite; analysis aborted")
    invalid = (reference_boot <= 0) | ~np.isfinite(reference_boot)
    if invalid.any():
        replicate, target = np.argwhere(invalid)[0]
        raise ValueError(f"Resampled reference denominator MSE is zero/nonfinite at draw {replicate}, target {TARGETS[target]}; analysis aborted")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        effect = float(1.0 - np.mean(candidate / reference))
        bootstrap_effects = 1.0 - np.mean(candidate_boot / reference_boot, axis=1)
    if not np.isfinite(effect) or not np.isfinite(bootstrap_effects).all():
        raise ValueError("Original or resampled ratio statistic is nonfinite; analysis aborted")
    roots = bootstrap_effects - effect
    tail_count = int(np.count_nonzero(roots >= effect))
    quantiles = np.quantile(bootstrap_effects, [0.025, 0.975], method="linear")
    return {
        "effect": effect,
        "ci_low": float(2 * effect - quantiles[1]),
        "ci_high": float(2 * effect - quantiles[0]),
        "p_value": float((1 + tail_count) / (len(bootstrap_effects) + 1)),
        "tail_count": tail_count,
        "replicates": int(len(bootstrap_effects)),
        "bootstrap_min": float(bootstrap_effects.min()),
        "bootstrap_max": float(bootstrap_effects.max()),
        "bootstrap_degenerate": bool(np.ptp(bootstrap_effects) == 0),
    }


def compare_loss_arrays(factor, reference, indices):
    """Compare T x 6 loss arrays using jointly supplied bootstrap indices.

    G=1-mean_i(mean_t F / mean_t R).  Both target means are recomputed per
    draw.  The p-value uses G_b-G_hat and the interval is basic, unbounded,
    marginal 95%, using linear quantiles.  Invalid denominators abort rather
    than adding epsilon or dropping draws/targets.
    """
    factor = _checked_losses(factor, "factor")
    reference = _checked_losses(reference, "reference")
    if factor.shape != reference.shape:
        raise ValueError("factor and reference must have identical shapes")
    indices = _checked_indices(indices, len(factor))
    result = _comparison_statistics(_loss_means(factor, indices), _loss_means(reference, indices))
    result.update(n_dates=int(len(factor)), n_targets=len(TARGETS))
    return result


def _history_label(value):
    if isinstance(value, str) and value.strip() == "expanding":
        return "expanding"
    if isinstance(value, bool):
        raise ValueError("Invalid coefficient history label")
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid coefficient history label: {value!r}") from None
    if not np.isfinite(number) or number not in (104, 260, 520):
        raise ValueError(f"Invalid coefficient history label: {value!r}")
    return str(int(number))


def _checked_predictions(predictions, part, config):
    required = {"weighting", "target", "policy_id", "stage", "origin_date", "response_date", "actual", "prediction"}
    if not required.issubset(predictions.columns):
        raise ValueError(f"Missing prediction columns: {sorted(required.difference(predictions.columns))}")
    frame = predictions.copy()
    if frame.empty or frame[list(required)].isna().any().any():
        raise ValueError("Prediction inputs must be nonempty and required fields nonmissing")
    for column in ("origin_date", "response_date"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
        if frame[column].dt.tz is not None:
            raise ValueError("Forecast calendar dates must be timezone-free")
    if ((frame.response_date - frame.origin_date) != pd.Timedelta(days=7)).any():
        raise ValueError("Each response must be exactly one calendar week after its origin")
    if (frame.response_date.dt.dayofweek != 4).any():
        raise ValueError("Response dates must be Friday labels")
    if part == "A":
        settings = config.get("part_a", {})
        start = settings.get("evaluation_response_start", "2022-01-01")
        end = settings.get("evaluation_response_end", "2024-12-31")
    else:
        settings = config.get("part_b", {}).get("calendar", {})
        start = settings.get("new_final_response_start", "2025-01-03")
        end = settings.get("new_final_response_end", "2026-08-28")
    frame = frame[(frame.stage == "final") & frame.response_date.between(pd.Timestamp(start), pd.Timestamp(end))].copy()
    if frame.empty:
        raise ValueError(f"Part {part} requires final-stage forecasts in its declared evaluation interval")
    histories = [column for column in ("history", "coefficient_history", "history_length", "coefficient_history_pairs") if column in frame]
    if not histories and part == "B":
        raise ValueError("Part B predictions require a coefficient history column")
    if histories:
        labels = [frame[column].map(_history_label) for column in histories]
        if any(not labels[0].equals(label) for label in labels[1:]):
            raise ValueError("Conflicting coefficient history columns")
        frame["history"] = labels[0]
    else:
        frame["history"] = "expanding"
    expected_histories = {"expanding"} if part == "A" else set(HISTORIES)
    if set(frame.history) != expected_histories:
        raise ValueError(f"Part {part} requires histories {sorted(expected_histories)}")
    if tuple(config.get("design", {}).get("targets", TARGETS)) != TARGETS or set(frame.target) != set(TARGETS):
        raise ValueError("Inference requires exactly the fixed six targets in the declared S order")
    if set(frame.weighting) != {"value", "equal"}:
        raise ValueError("Inference requires both value and equal weightings")
    for column in ("prediction", "actual"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not np.isfinite(frame[column].to_numpy()).all():
            raise ValueError("Forecasts and actual outcomes must be finite")
    with np.errstate(over="ignore", invalid="ignore"):
        squared = (frame.prediction.to_numpy() - frame.actual.to_numpy()) ** 2
    if not np.isfinite(squared).all():
        raise ValueError("Squared forecast losses must be finite")
    if "squared_error" in frame:
        supplied = pd.to_numeric(frame.squared_error, errors="raise").to_numpy()
        if not np.allclose(supplied, squared, rtol=1e-9, atol=1e-12):
            raise ValueError("Stored squared errors disagree with forecasts and actuals")
    frame["squared_error"] = squared
    if "absolute_error" in frame:
        supplied = pd.to_numeric(frame.absolute_error, errors="raise").to_numpy()
        if not np.allclose(supplied, np.sqrt(squared), rtol=1e-9, atol=1e-12):
            raise ValueError("Stored absolute errors disagree with forecasts and actuals")
    keys = ["weighting", "history", "policy_id", "target"]
    if frame.duplicated(keys + ["origin_date"]).any():
        raise ValueError("Duplicate forecast keys")
    if (frame.groupby(["weighting", "target", "origin_date", "response_date"]).actual.nunique() != 1).any():
        raise ValueError("Actual outcomes disagree across policies or history rules")
    dates = frame[["origin_date", "response_date"]].drop_duplicates().sort_values("origin_date").reset_index(drop=True)
    n_dates = len(dates)
    # Every supplied cell, including secondary cells, uses this same calendar.
    expected_policies = frozenset(frame.policy_id)
    required_policies = {FACTOR_POLICY, *REFERENCE_POLICIES}
    if not required_policies.issubset(expected_policies):
        raise ValueError("A required fixed factor or reference policy is missing")
    for weighting in ("value", "equal"):
        for history in sorted(expected_histories):
            subset = frame[(frame.weighting == weighting) & (frame.history == history)]
            if frozenset(subset.policy_id) != expected_policies:
                raise ValueError("Every history and weighting must contain the same policies")
            for policy in expected_policies:
                cell = subset[subset.policy_id == policy]
                if set(cell.target) != set(TARGETS):
                    raise ValueError("A policy/history/weighting cell is missing a target")
                for target in TARGETS:
                    observed = cell[cell.target == target][["origin_date", "response_date"]].sort_values("origin_date").reset_index(drop=True)
                    if len(observed) != n_dates or not observed.equals(dates):
                        raise ValueError("All policies, targets, histories and weightings must use identical eligible date order")
    return frame, dates


def _index_fingerprint(indices):
    """Hash little-endian int64 shape followed by little-endian C-order data."""
    digest = hashlib.sha256()
    digest.update(np.asarray(indices.shape, dtype="<i8").tobytes(order="C"))
    digest.update(np.asarray(indices, dtype="<i8", order="C").tobytes(order="C"))
    return digest.hexdigest()


def _comparisons(part):
    histories = ("expanding",) if part == "A" else HISTORIES
    cells = []
    for history in histories:
        for reference in REFERENCE_POLICIES:
            cells.append({
                "comparison_id": f"factor_vs_{reference.split('__')[0]}__history-{history}",
                "comparison_kind": "factor_vs_reference",
                "candidate_policy": FACTOR_POLICY, "reference_policy": reference,
                "candidate_history": history, "reference_history": history,
            })
    if part == "B":
        for history in HISTORIES[:-1]:
            cells.append({
                "comparison_id": f"factor_history-{history}_vs_expanding",
                "comparison_kind": "history_vs_expanding",
                "candidate_policy": FACTOR_POLICY, "reference_policy": FACTOR_POLICY,
                "candidate_history": history, "reference_history": "expanding",
            })
    return cells


def run_inference(predictions: pd.DataFrame, part="A", config=None, output: Path | None = None):
    """Return all fixed comparisons and recoverable joint-index metadata.

    Exactly one matrix is drawn per part/evaluation/block setting and reused
    across both weightings and all comparisons.  Holm adjustment is separate
    for each weighting and block setting (4 tests in A, 19 in B).  Part B never
    computes development p-values.  Optional output writes only the returned
    result CSV, compressed index matrices and JSON index manifest, without
    saving/refitting model state.
    """
    if part not in ("A", "B"):
        raise ValueError("part must be 'A' or 'B'")
    config = {} if config is None else config
    if config.get("design", {}).get("primary_factor_policy_all_histories", FACTOR_POLICY) != FACTOR_POLICY:
        raise ValueError("The primary factor policy must remain the frozen Experiment 1 procedure")
    settings = config.get("inference", {})
    replicates = _positive_integer(settings.get("replicates", 9999), "replicates")
    primary_block = settings.get("expected_block_length_dates", 13)
    blocks = [primary_block, *settings.get("sensitivity_block_lengths_dates", [6, 26])]
    if len(set(blocks)) != len(blocks):
        raise ValueError("Primary and sensitivity block lengths must be distinct")
    seed = settings.get("seed", 20261031)
    alpha = settings.get("alpha", 0.05)
    if not isinstance(alpha, Real) or isinstance(alpha, bool) or not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0,1)")
    frame, dates = _checked_predictions(predictions, part, config)
    n_dates = len(dates)
    losses = {}
    for (weighting, history, policy), group in frame.groupby(["weighting", "history", "policy_id"], sort=False):
        table = group.pivot(index="origin_date", columns="target", values="squared_error")
        losses[(weighting, history, policy)] = table.reindex(index=dates.origin_date, columns=TARGETS).to_numpy()
    manifest = {
        "part": part, "evaluation_stage": "final", "replicates": replicates,
        "seed": int(seed), "rng": "numpy.Generator(PCG64)", "target_order": list(TARGETS),
        "n_dates": n_dates, "n_targets": len(TARGETS),
        "response_dates": dates.response_date.dt.strftime("%Y-%m-%d").tolist(),
        "origin_dates": dates.origin_date.dt.strftime("%Y-%m-%d").tolist(),
        "index_hash_format": "sha256(shape_as_little_endian_int64_then_C_order_little_endian_int64_data)",
        "shared_across_weightings_targets_policies_histories": True,
        "reset_seed_per_part_stage_block_setting": True,
        "matrices": {},
    }
    comparisons = _comparisons(part)
    family_size = 4 if part == "A" else 19
    rows = []
    matrices_to_save = {}
    for block_length in blocks:
        indices = stationary_indices(n_dates, replicates, block_length, seed)
        fingerprint = _index_fingerprint(indices)
        manifest["matrices"][str(block_length)] = {
            "block_length": block_length, "shape": [replicates, n_dates],
            "dtype": "<i8", "sha256": fingerprint,
            "is_primary_block": block_length == primary_block,
        }
        if output is not None:
            filename = f"indices_b{block_length}.npz"
            matrices_to_save[filename] = indices
            manifest["matrices"][str(block_length)]["file"] = filename
        cache = {}
        for weighting in ("value", "equal"):
            family = []
            for comparison in comparisons:
                candidate_key = (weighting, comparison["candidate_history"], comparison["candidate_policy"])
                reference_key = (weighting, comparison["reference_history"], comparison["reference_policy"])
                for key in (candidate_key, reference_key):
                    if key not in cache:
                        cache[key] = _loss_means(losses[key], indices)
                try:
                    result = _comparison_statistics(cache[candidate_key], cache[reference_key])
                except ValueError as error:
                    raise ValueError(f"Part {part}, {weighting}, b={block_length}, {comparison['comparison_id']}: {error}") from error
                result.update(comparison)
                result.update({
                    "part": part, "stage": "final", "weighting": weighting,
                    "block_length": block_length, "is_primary_block": block_length == primary_block,
                    "is_primary_weighting": weighting == "value",
                    "is_primary": block_length == primary_block and weighting == "value",
                    "evidence_status": "exploratory_post_pilot" if part == "A" else "approximate_frozen_procedure_evaluation",
                    "family_size": family_size, "family_id": f"{part}_{weighting}_b{block_length}",
                    "n_dates": n_dates, "n_targets": len(TARGETS), "index_sha256": fingerprint,
                })
                result["effect_pct"] = 100 * result["effect"]
                result["ci_low_pct"] = 100 * result["ci_low"]
                result["ci_high_pct"] = 100 * result["ci_high"]
                family.append(result)
            adjusted = holm_adjust([row["p_value"] for row in family])
            for row, adjusted_p in zip(family, adjusted):
                row["p_adjusted"] = float(adjusted_p)
                row["reject_adjusted"] = bool(row["effect"] > 0 and adjusted_p < alpha)
            rows.extend(family)
    results = pd.DataFrame(rows)
    if output is not None:
        output = Path(output)
        paths = [output / "inference.csv", output / "bootstrap_index_manifest.json"]
        if any(path.exists() for path in paths + [output / name for name in matrices_to_save]):
            raise FileExistsError("Inference output files already exist; use a new directory")
        output.mkdir(parents=True, exist_ok=True)
        for filename, indices in matrices_to_save.items():
            np.savez_compressed(output / filename, indices=np.asarray(indices, dtype="<i8", order="C"))
        for entry in manifest["matrices"].values():
            entry["file_sha256"] = hashlib.sha256((output / entry["file"]).read_bytes()).hexdigest()
        results.to_csv(paths[0], index=False)
        paths[1].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results, manifest
