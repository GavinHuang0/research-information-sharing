"""Paired, target-balanced reporting for the fixed empirical pilot.

All summaries are rebuilt from forecast-level observations.  The primary
aggregate is the equal-target mean of MSE ratios to each target's own-history
forecast; it is deliberately not a ratio of pooled MSEs.  Selection is confined
to the value-weighted development sample.  Plots do not choose new winners.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd


_KEYS = ["weighting", "stage", "policy_id", "target"]
_METADATA = [
    "method", "measurement_panel", "outcome_panel", "n_measurements",
    "n_outcomes", "n_factors",
]


def _validated_predictions(predictions):
    required = set(_KEYS + ["method", "origin_date", "response_date", "prediction", "actual"])
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Prediction table is missing columns: {sorted(missing)}")
    if predictions.empty:
        raise ValueError("Prediction table must not be empty")
    frame = predictions.copy()
    if frame[list(required)].isna().any().any():
        raise ValueError("Required prediction fields must not be missing")
    for column in ("origin_date", "response_date"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    if (frame.response_date <= frame.origin_date).any():
        raise ValueError("Responses must follow their forecast origins")
    if frame.duplicated(_KEYS + ["origin_date"]).any():
        raise ValueError("Duplicate forecast origins within a policy and target")
    if frame.duplicated(["weighting", "policy_id", "target", "origin_date"]).any():
        raise ValueError("A forecast origin occurs in more than one stage")
    for column in ("actual", "prediction"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not np.isfinite(frame[column].to_numpy()).all():
            raise ValueError(f"{column} must contain only finite values")
    errors = frame.prediction.to_numpy() - frame.actual.to_numpy()
    losses = {"squared_error": errors ** 2, "absolute_error": np.abs(errors)}
    for column, recomputed in losses.items():
        if not np.isfinite(recomputed).all():
            raise ValueError("Forecast losses must be finite")
        if column in frame:
            supplied = pd.to_numeric(frame[column], errors="raise").to_numpy()
            if not np.allclose(supplied, recomputed, rtol=1e-9, atol=1e-12):
                raise ValueError(f"Stored {column} does not match predictions and actuals")
        frame[column] = recomputed

    # Every cell compares exactly the same calendar pairs, including across
    # targets and portfolio weightings.  Missing models cannot silently change
    # the reported target mix or observation sample.
    expected_dates = {}
    expected_targets = None
    expected_policies = None
    for (weighting, stage), cell in frame.groupby(["weighting", "stage"], sort=False):
        targets = frozenset(cell.target)
        policies = frozenset(cell.policy_id)
        if expected_targets is None:
            expected_targets, expected_policies = targets, policies
        elif targets != expected_targets or policies != expected_policies:
            raise ValueError("All weighting/stage cells must contain the same targets and policies")
        for target in targets:
            target_cell = cell[cell.target == target]
            if frozenset(target_cell.policy_id) != policies:
                raise ValueError("A target is missing a policy")
            for policy, group in target_cell.groupby("policy_id", sort=False):
                dates = frozenset(zip(group.origin_date, group.response_date))
                if stage not in expected_dates:
                    expected_dates[stage] = dates
                elif dates != expected_dates[stage]:
                    raise ValueError("Policies, targets and weightings must use identical eligible dates within each stage")
        actual_counts = cell.groupby(["target", "origin_date", "response_date"]).actual.nunique()
        if (actual_counts != 1).any():
            raise ValueError("Policies disagree about a target's realized outcome")
    metadata = [column for column in _METADATA if column in frame]
    for column in metadata:
        if frame[column].isna().any():
            raise ValueError(f"Policy metadata {column} must not be missing")
        if (frame.groupby("policy_id")[column].nunique() != 1).any():
            raise ValueError(f"Policy metadata {column} changes across observations")
    return frame


def summarize(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return checked per-target losses and equal-target ratio aggregates.

    Each target needs exactly one policy whose method is ``local_history``.
    Zero baseline loss is rejected because relative performance is undefined.
    Date pairs must agree across every policy, target and weighting in a stage.
    """
    frame = _validated_predictions(predictions)
    metadata = [column for column in _METADATA if column in frame]
    per_target = frame.groupby(_KEYS, sort=True).agg(
        n_forecasts=("actual", "size"), mse=("squared_error", "mean"),
        mae=("absolute_error", "mean"),
    ).reset_index()
    info = frame[_KEYS + metadata].drop_duplicates()
    per_target = per_target.merge(info, on=_KEYS, validate="one_to_one")
    baseline = per_target[per_target.method == "local_history"]
    baseline_keys = ["weighting", "stage", "target"]
    if baseline.duplicated(baseline_keys).any():
        raise ValueError("Each target/stage/weighting needs exactly one local_history baseline")
    baseline = baseline[baseline_keys + ["mse", "mae"]].rename(
        columns={"mse": "baseline_mse", "mae": "baseline_mae"}
    )
    per_target = per_target.merge(baseline, on=baseline_keys, how="left", validate="many_to_one")
    if per_target[["baseline_mse", "baseline_mae"]].isna().any().any():
        raise ValueError("Each target/stage/weighting needs a local_history baseline")
    if (per_target[["baseline_mse", "baseline_mae"]] <= 0).any().any():
        raise ValueError("Baseline MSE and MAE must be positive for relative losses")
    per_target["ratio_mse"] = per_target.mse / per_target.baseline_mse
    per_target["improvement_pct"] = 100.0 * (1.0 - per_target.ratio_mse)
    per_target["ratio_mae"] = per_target.mae / per_target.baseline_mae
    aggregate_keys = ["weighting", "stage", "policy_id"]
    aggregate = per_target.groupby(aggregate_keys, sort=True).agg(
        n_targets=("target", "nunique"),
        n_forecasts_per_target=("n_forecasts", "first"),
        mean_ratio_mse=("ratio_mse", "mean"),
        mean_mse=("mse", "mean"),
        mean_mae=("mae", "mean"),
        mean_ratio_mae=("ratio_mae", "mean"),
    ).reset_index()
    aggregate["improvement_pct"] = 100.0 * (1.0 - aggregate.mean_ratio_mse)
    aggregate["mae_improvement_pct"] = 100.0 * (1.0 - aggregate.mean_ratio_mae)
    aggregate = aggregate.merge(
        per_target[aggregate_keys + metadata].drop_duplicates(),
        on=aggregate_keys, validate="one_to_one",
    )
    return per_target, aggregate


def _factor_mask(frame):
    return (frame.method.astype(str).str.startswith("factor_")
            | frame.policy_id.astype(str).str.startswith("factor"))


def choose_winners(aggregate: pd.DataFrame) -> dict[str, str]:
    """Freeze one overall and one factor policy using development/value only.

    Ties resolve lexicographically by policy ID.  Final-stage and equal-weighted
    losses cannot influence either choice.
    """
    required = {"weighting", "stage", "policy_id", "method", "mean_ratio_mse"}
    if not required.issubset(aggregate):
        raise ValueError(f"Aggregate table is missing columns: {sorted(required.difference(aggregate.columns))}")
    development = aggregate[(aggregate.weighting == "value") & (aggregate.stage == "development")].copy()
    if development.empty:
        raise ValueError("Winner selection requires value-weighted development results")
    if development.policy_id.duplicated().any():
        raise ValueError("Development summary contains duplicate policy IDs")
    if not np.isfinite(development.mean_ratio_mse.to_numpy()).all():
        raise ValueError("Development MSE ratios must be finite")
    ordered = development.sort_values(["mean_ratio_mse", "policy_id"], kind="stable")
    factors = ordered[_factor_mask(ordered)]
    if factors.empty:
        raise ValueError("Winner selection requires at least one factor policy")
    return {"overall": str(ordered.iloc[0].policy_id), "factor": str(factors.iloc[0].policy_id)}


def _save_figure(figure, output, name, plt):
    figure.savefig(output / f"{name}.png", dpi=180, bbox_inches="tight")
    figure.savefig(output / f"{name}.pdf", bbox_inches="tight")
    plt.close(figure)


def _heatmap(axis, values, row_labels, column_labels, title, plt, limit=None):
    values = np.asarray(values, dtype=float)
    if limit is None:
        finite = np.abs(values[np.isfinite(values)])
        limit = max(float(finite.max()) if finite.size else 0.0, 1.0)
    artist = axis.imshow(np.ma.masked_invalid(values), cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
    axis.set_xticks(range(len(column_labels)), column_labels, rotation=30, ha="right")
    axis.set_yticks(range(len(row_labels)), row_labels)
    axis.set_title(title)
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            value = values[row, column]
            if np.isfinite(value):
                axis.text(column, row, f"{value:.1f}", ha="center", va="center", fontsize=8)
    return artist


def write_reports(predictions: pd.DataFrame, output: Path, winners: dict[str, str]):
    """Write checked CSV tables and four pairs of PNG/PDF figures.

    ``winners`` must be frozen from the development/value results.  No winner
    is selected using the final sample or the equal-weighted robustness data.
    Confidence intervals are intentionally omitted: these plots describe the
    fixed policies and do not imply independent industries or forecast dates.
    """
    per_target, aggregate = summarize(predictions)
    expected_winners = choose_winners(aggregate)
    if any(winners.get(role) != policy for role, policy in expected_winners.items()):
        raise ValueError("Winners must match the frozen value-weighted development choices")
    # Matplotlib is optional for ordinary package use and needed only here.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    per_target.to_csv(output / "target_summary.csv", index=False)
    aggregate.to_csv(output / "aggregate_summary.csv", index=False)
    (output / "selected_policies.json").write_text(
        json.dumps({"selection_stage": "development", "selection_weighting": "value", **expected_winners}, indent=2) + "\n",
        encoding="utf-8",
    )
    stages = [stage for stage in ("development", "final") if stage in set(aggregate.stage)]
    weightings = [weight for weight in ("value", "equal") if weight in set(aggregate.weighting)]
    policy_order = aggregate[(aggregate.stage == "development") & (aggregate.weighting == "value")].sort_values(
        ["mean_ratio_mse", "policy_id"], kind="stable"
    ).policy_id.tolist()
    colors = ["#147d92" if policy == winners["overall"] else
              "#99599c" if policy == winners["factor"] else "#a8b5bd" for policy in policy_order]
    with plt.rc_context({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False}):
        figure, axes = plt.subplots(len(stages), len(weightings), figsize=(8.5 * len(weightings), 6.6 * len(stages)), squeeze=False)
        for row, stage in enumerate(stages):
            for column, weighting in enumerate(weightings):
                axis = axes[row, column]
                cell = aggregate[(aggregate.stage == stage) & (aggregate.weighting == weighting)].set_index("policy_id").reindex(policy_order)
                axis.barh(policy_order, cell.improvement_pct, color=colors)
                axis.invert_yaxis()
                axis.axvline(0, color="#333333", linewidth=0.8)
                axis.set_title(f"{stage.capitalize()} | {weighting}-weighted")
                axis.set_xlabel("Improvement in equal-target mean MSE ratio (%)")
                axis.grid(axis="x", alpha=0.2)
        figure.suptitle("All fixed policies versus each target's own-history forecast\nTeal: frozen overall choice; purple: frozen factor choice", fontsize=12)
        figure.tight_layout(rect=(0, 0, 1, 0.96))
        _save_figure(figure, output, "aggregate_relative_improvement", plt)

        final = per_target[per_target.stage == "final"]
        if not final.empty:
            targets = sorted(final.target.unique())
            limit = max(float(final.improvement_pct.abs().max()), 1.0)
            figure, axes = plt.subplots(1, len(weightings), figsize=(8.5 * len(weightings), 10), squeeze=False)
            for column, weighting in enumerate(weightings):
                table = final[final.weighting == weighting].pivot(index="policy_id", columns="target", values="improvement_pct").reindex(index=policy_order, columns=targets)
                artist = _heatmap(axes[0, column], table.to_numpy(), policy_order, targets,
                                  f"Final | {weighting}-weighted", plt, limit)
                figure.colorbar(artist, ax=axes[0, column], label="MSE improvement versus own history (%)", shrink=0.7)
            figure.suptitle("Final sample: every policy and target; choices remain frozen", fontsize=12)
            figure.tight_layout(rect=(0, 0, 1, 0.96))
            _save_figure(figure, output, "final_target_improvement", plt)

        factors = aggregate[_factor_mask(aggregate)]
        mechanism_fields = {"n_measurements", "n_outcomes", "method"}
        if not factors.empty and mechanism_fields.issubset(factors):
            measurements = sorted(factors.n_measurements.unique())
            outcomes = sorted(value for value in factors.n_outcomes.unique() if value != 1)
            specifications = [("factor_separate", 1, "Separate | O=target")]
            for method, label in (("factor_pooled", "Common"), ("factor_partial", "Partial")):
                specifications.extend((method, value, f"{label} | O={int(value)}") for value in outcomes)
            limit = max(float(factors.improvement_pct.abs().max()), 1.0)
            figure, axes = plt.subplots(len(stages), len(weightings), figsize=(6.2 * len(weightings), 4.2 * len(stages)), squeeze=False)
            for row, stage in enumerate(stages):
                for column, weighting in enumerate(weightings):
                    cell = factors[(factors.stage == stage) & (factors.weighting == weighting)]
                    values = np.full((len(specifications), len(measurements)), np.nan)
                    for i, (method, outcome_count, _) in enumerate(specifications):
                        for j, measurement_count in enumerate(measurements):
                            selected = cell[(cell.method == method) & (cell.n_outcomes == outcome_count) & (cell.n_measurements == measurement_count)]
                            if len(selected) > 1:
                                raise ValueError("Multiple factor policies occupy one mechanism cell")
                            if len(selected) == 1:
                                values[i, j] = float(selected.iloc[0].improvement_pct)
                    artist = _heatmap(axes[row, column], values, [s[2] for s in specifications],
                                      [f"M={int(value)}" for value in measurements],
                                      f"{stage.capitalize()} | {weighting}-weighted", plt, limit)
                    figure.colorbar(artist, ax=axes[row, column], label="Improvement (%)", shrink=0.7)
            figure.suptitle("Factor measurement breadth and coefficient sharing (fixed K)", fontsize=12)
            figure.tight_layout(rect=(0, 0, 1, 0.95))
            _save_figure(figure, output, "factor_mechanisms", plt)

        if not final.empty:
            frame = _validated_predictions(predictions)
            frame = frame[frame.stage == "final"]
            baseline = frame[frame.method == "local_history"][["weighting", "target", "origin_date", "squared_error"]].rename(columns={"squared_error": "baseline_error"})
            figure, axes = plt.subplots(2, len(weightings), figsize=(8 * len(weightings), 8.5), squeeze=False)
            for row, role in enumerate(("overall", "factor")):
                policy = winners[role]
                selected = frame[frame.policy_id == policy].merge(baseline, on=["weighting", "target", "origin_date"], validate="one_to_one")
                selected["paired_difference"] = selected.squared_error - selected.baseline_error
                for column, weighting in enumerate(weightings):
                    axis = axes[row, column]
                    cell = selected[selected.weighting == weighting]
                    for target, group in cell.groupby("target", sort=True):
                        group = group.sort_values("origin_date")
                        axis.plot(group.origin_date, group.paired_difference.cumsum(), label=target, linewidth=1)
                    average = cell.groupby("origin_date", sort=True).paired_difference.mean()
                    axis.plot(average.index, average.cumsum(), color="black", linewidth=2, label="Equal-target mean")
                    axis.axhline(0, color="#666666", linewidth=0.8)
                    axis.set_title(f"Frozen {role}: {policy}\nFinal | {weighting}-weighted")
                    axis.set_ylabel("Cumulative squared-error difference")
                    axis.grid(alpha=0.2)
                    axis.legend(fontsize=7, ncol=2)
                    axis.tick_params(axis="x", rotation=25)
            figure.suptitle("Paired loss against own history; negative favors the frozen policy", fontsize=12)
            figure.tight_layout(rect=(0, 0, 1, 0.95))
            _save_figure(figure, output, "final_cumulative_paired_loss", plt)
    return per_target, aggregate
