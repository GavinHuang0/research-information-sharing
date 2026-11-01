"""Bounded synthetic diagnostics for the stationary loss-bootstrap engine.

No returns, forecast files, models, or empirical results are read.  Diagnostics
concern a single raw comparison under stationary synthetic loss processes,
not the complete generated-factor/tuning pipeline or Holm-family power.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from factorcast.bootstrap import compare_loss_arrays, stationary_indices  # noqa: E402


def _ar1(rng, n_dates, n_series, rho, innovation_sd):
    """Gaussian AR(1) initialized from its stationary distribution."""
    values = np.empty((n_dates, n_series), dtype=float)
    values[0] = rng.normal(scale=innovation_sd / np.sqrt(1 - rho ** 2), size=n_series)
    for date in range(1, n_dates):
        values[date] = rho * values[date - 1] + rng.normal(scale=innovation_sd, size=n_series)
    return values


def stationary_loss_pair(rng, n_dates):
    """Positive paired losses with equal marginal means for every target.

    Shared market/target shocks create paired dependence.  Independent,
    identically distributed candidate/reference AR components are exchangeable
    across models.  Multiplying the candidate by exp(-delta) changes the true
    ratio advantage from zero to 1-exp(-delta), without pointwise dominance.
    """
    common = _ar1(rng, n_dates, 1, 0.65, 0.20)
    target = _ar1(rng, n_dates, 6, 0.35, 0.10)
    candidate_shared = _ar1(rng, n_dates, 1, 0.4, 0.16)
    reference_shared = _ar1(rng, n_dates, 1, 0.4, 0.16)
    candidate_specific = _ar1(rng, n_dates, 6, 0.25, 0.10)
    reference_specific = _ar1(rng, n_dates, 6, 0.25, 0.10)
    scales = np.array([1.0, 0.8, 1.2, 1.5, 0.7, 1.1])
    candidate = scales * np.exp(common + target + candidate_shared + candidate_specific)
    reference = scales * np.exp(common + target + reference_shared + reference_specific)
    return candidate, reference


def _binomial_summary(successes, replications):
    rate = successes / replications
    z = 1.959963984540054
    denominator = 1 + z ** 2 / replications
    center = (rate + z ** 2 / (2 * replications)) / denominator
    half_width = z * math.sqrt(rate * (1 - rate) / replications
                               + z ** 2 / (4 * replications ** 2)) / denominator
    return {
        "count": int(successes), "replications": replications, "rate": rate,
        "monte_carlo_standard_error": math.sqrt(rate * (1 - rate) / replications),
        "wilson_95_interval": [center - half_width, center + half_width],
    }


def diagnose(replications=100, bootstrap_replicates=499):
    """Run the fixed two-length, null/shifted-positive diagnostic design."""
    if replications not in (100, 200) or bootstrap_replicates not in (499, 999):
        raise ValueError("Bounded diagnostics require R=100/200 and B=499/999")
    started = time.perf_counter()
    scenarios = []
    for n_dates in (87, 156):
        # Reusing the exact PCG64 matrix matches the declared seed-reset rule
        # and keeps common random bootstrap indices across synthetic datasets.
        indices = stationary_indices(n_dates, bootstrap_replicates, 13, 20261031)
        rng = np.random.Generator(np.random.PCG64(20261101 + n_dates))
        records = {"equal_marginal_null": [], "shifted_positive": []}
        for _ in range(replications):
            candidate, reference = stationary_loss_pair(rng, n_dates)
            records["equal_marginal_null"].append(compare_loss_arrays(candidate, reference, indices))
            records["shifted_positive"].append(compare_loss_arrays(candidate * np.exp(-0.15), reference, indices))
        for name, comparisons in records.items():
            true_effect = 0.0 if name == "equal_marginal_null" else float(1 - np.exp(-0.15))
            rejections = sum(item["effect"] > 0 and item["p_value"] < 0.05 for item in comparisons)
            covered = sum(item["ci_low"] <= true_effect <= item["ci_high"] for item in comparisons)
            scenarios.append({
                "scenario": name, "n_dates": n_dates, "n_targets": 6,
                "true_population_ratio_advantage": true_effect,
                "rejection": _binomial_summary(rejections, replications),
                "marginal_basic_95_coverage": _binomial_summary(covered, replications),
                "mean_estimated_effect": float(np.mean([item["effect"] for item in comparisons])),
                "mean_raw_p_value": float(np.mean([item["p_value"] for item in comparisons])),
                "mean_interval_width": float(np.mean([item["ci_high"] - item["ci_low"] for item in comparisons])),
                "degenerate_bootstrap_count": sum(item["bootstrap_degenerate"] for item in comparisons),
            })
    return {
        "scope": "synthetic_stationary_loss_process_single_comparison_diagnostics_only",
        "not_full_learning_pipeline_calibration": True,
        "not_Holm4_or_Holm19_family_calibration": True,
        "settings": {
            "monte_carlo_replications": replications, "bootstrap_replicates": bootstrap_replicates,
            "n_dates": [87, 156], "expected_block_length": 13,
            "block_length_selected_from_diagnostics": False,
            "bootstrap_seed": 20261031, "data_seed_rule": "20261101_plus_n_dates",
            "rng": "numpy.Generator(PCG64)", "numpy_version": np.__version__,
            "bootstrap_indices_reused_across_synthetic_replications": True,
            "null": "exchangeable_stationary_model_shocks_equal_marginal_loss_means",
            "positive_shift_log_scale": -0.15,
            "test": "single_unadjusted_one_sided_p_below_0.05_and_positive_effect",
            "interval": "basic_two_sided_95_marginal_linear_quantiles",
            "no_empirical_data_or_models": True,
        },
        "scenarios": scenarios,
        "interpretation": (
            "Rates have Monte Carlo uncertainty and describe only these stationary synthetic losses. "
            "They do not prove nominal size/coverage for the full expanding-PCA, rolling/expanding "
            "coefficient, tuned, nested forecast pipeline. Report adverse diagnostics without "
            "changing the primary block length or selecting a favorable seed."
        ),
        "elapsed_seconds": time.perf_counter() - started,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replications", type=int, choices=(100, 200), default=100)
    parser.add_argument("--bootstrap-replicates", type=int, choices=(499, 999), default=499)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / ".venv" / "bootstrap_synthetic_validation.json")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Synthetic validation output already exists; use a new path")
    report = diagnose(args.replications, args.bootstrap_replicates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "scenarios": report["scenarios"],
                      "elapsed_seconds": report["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
