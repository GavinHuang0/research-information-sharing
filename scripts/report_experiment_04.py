"""Summarize the paired forecasts from Experiment 4 without inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/experiment-04-2026-11-23"
GROUP = ["weighting", "period", "history"]
CONTRASTS = (
    ("compression_ols", "pc_ols", "panel_ols"),
    ("compression_ridge", "pc_ridge", "panel_ridge"),
    ("full_panel_shrinkage", "panel_ridge", "panel_ols"),
    ("two_pc_shrinkage", "pc_ridge", "pc_ols"),
    ("unpenalized_pcs_vs_own", "pc_ols", "own_ols"),
    ("own_history_ridge", "own_ridge", "own_ols"),
    ("own_history_elasticnet", "own_elasticnet", "own_ols"),
    ("pcs_beyond_own_ridge", "own_ridge_plus_pcs", "own_ridge"),
    ("pooling", "pc_common", "pc_ols"),
    ("panel_ridge_vs_legacy", "panel_ridge", "panel_ridge_legacy"),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(forecasts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    target_group = GROUP + ["target"]
    target = (
        forecasts.groupby(target_group + ["method"], sort=False, as_index=False)
        .agg(mse=("squared_error", "mean"), n_dates=("squared_error", "size"))
    )
    mse = target.pivot(index=target_group, columns="method", values="mse")
    if not np.isfinite(mse.to_numpy()).all() or (mse <= 0).any().any():
        raise ValueError("Summary requires complete and positive target-specific MSEs")
    own = mse["own_ols"].rename("own_mse").reset_index()
    target = target.merge(own, on=target_group, validate="many_to_one")
    target["gain_vs_own_ols_pct"] = 100 * (1 - target["mse"] / target["own_mse"])
    summary = (
        target.groupby(GROUP + ["method"], sort=False, as_index=False)
        .agg(mean_target_mse=("mse", "mean"),
             gain_vs_own_ols_pct=("gain_vs_own_ols_pct", "mean"),
             n_targets=("target", "size"), n_dates=("n_dates", "min"))
    )
    contrasts = []
    for comparison, candidate, reference in CONTRASTS:
        pair = mse[[candidate, reference]].copy()
        pair.columns = ["candidate_mse", "reference_mse"]
        pair["gain_pct"] = 100 * (1 - pair["candidate_mse"] / pair["reference_mse"])
        result = pair.groupby(level=GROUP, sort=False).agg(
            gain_pct=("gain_pct", "mean"),
            candidate_mean_mse=("candidate_mse", "mean"),
            reference_mean_mse=("reference_mse", "mean"),
            n_targets=("gain_pct", "size"),
        ).reset_index()
        result.insert(3, "comparison", comparison)
        result.insert(4, "candidate", candidate)
        result.insert(5, "reference", reference)
        contrasts.append(result)
    return target, summary, pd.concat(contrasts, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = args.output / "predictions.csv.gz"
    forecasts = pd.read_csv(source, float_precision="round_trip")
    target, summary, contrasts = summarize(forecasts)
    reports = args.output / "reports"
    reports.mkdir(exist_ok=False)
    outputs = {"target_summary.csv": target, "summary.csv": summary, "contrasts.csv": contrasts}
    for name, frame in outputs.items():
        frame.to_csv(reports / name, index=False, lineterminator="\n")
    manifest = {
        "predictions_sha256": digest(source),
        "report_code_sha256_lf": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "files": {name: {"rows": len(frame), "sha256": digest(reports / name)} for name, frame in outputs.items()},
    }
    (reports / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Summarized {len(target)} target cells, {len(summary)} aggregate cells, and {len(contrasts)} contrasts.")


if __name__ == "__main__":
    main()
