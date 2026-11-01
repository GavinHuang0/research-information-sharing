"""All-history tables and prespecified Experiment 2 scientific figures.

No procedure is selected here. Confidence intervals are marginal basic
bootstrap intervals; Holm p-values refer to the declared comparison families.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd

from .pilot import S
from .pilot_reporting import summarize

FACTOR_POLICY = "factor_pooled__M-all__O-all"
REFERENCES = (
    "local_history__M-none__O-target", "ridge__M-all__O-target",
    "elasticnet__M-all__O-target", "pls__M-all__O-target",
)
REFERENCE_LABELS = ("Own history", "Ridge", "Elastic net", "PLS")
FIGURE_NAMES = (
    "part_a_fixed_forecast_uncertainty", "part_b_factor_vs_references",
    "part_b_finite_vs_expanding", "history_loss_curves",
    "final_target_history_improvement", "block_length_sensitivity",
)


def _history_order(values):
    values = set(str(value) for value in values)
    finite = sorted((value for value in values if value != "expanding"), key=int)
    return finite + (["expanding"] if "expanding" in values else [])


def summarize_history(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recompute every target/policy cell using its matching-history baseline."""
    if "history" not in predictions or predictions.empty or predictions.history.isna().any():
        raise ValueError("Nonempty predictions with explicit history labels are required")
    frame = predictions.copy()
    frame["history"] = frame.history.astype(str)
    for column in ("origin_date", "response_date"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    expected_cells, expected_dates = None, {}
    targets, aggregates = [], []
    for label in _history_order(frame.history):
        cell = frame.loc[frame.history == label]
        cells = frozenset(zip(cell.weighting, cell.stage, cell.target, cell.policy_id))
        if expected_cells is None:
            expected_cells = cells
        elif cells != expected_cells:
            raise ValueError("All histories must contain the same stages, weightings, targets, and policies")
        for stage, stage_rows in cell.groupby("stage"):
            dates = frozenset(zip(stage_rows.origin_date, stage_rows.response_date))
            if stage not in expected_dates:
                expected_dates[stage] = dates
            elif dates != expected_dates[stage]:
                raise ValueError("All histories must use identical calendar pairs within each stage")
        per_target, aggregate = summarize(cell.drop(columns="history"))
        per_target["history"], aggregate["history"] = label, label
        per_target["persistence_duplicate_across_histories"] = per_target.method == "persistence"
        aggregate["persistence_duplicate_across_histories"] = aggregate.method == "persistence"
        targets.append(per_target)
        aggregates.append(aggregate)
    if (frame.groupby(["weighting", "target", "origin_date", "response_date"]).actual.nunique() != 1).any():
        raise ValueError("Histories disagree on the realized target outcome")
    return pd.concat(targets, ignore_index=True), pd.concat(aggregates, ignore_index=True)


def _bootstrap_frame(frame, part):
    required = {
        "weighting", "comparison_kind", "candidate_policy", "reference_policy", "candidate_history",
        "reference_history", "block_length", "is_primary_block", "effect", "ci_low", "ci_high",
        "p_value", "p_adjusted",
    }
    missing = required.difference(frame.columns)
    if missing or frame.empty:
        raise ValueError(f"Part {part} bootstrap table is empty or missing {sorted(missing)}")
    result = frame.copy()
    if result[list(required)].isna().any().any():
        raise ValueError("Bootstrap fields must not be missing")
    for column in ("effect", "ci_low", "ci_high", "p_value", "p_adjusted", "block_length"):
        result[column] = pd.to_numeric(result[column], errors="raise")
        if not np.isfinite(result[column]).all():
            raise ValueError("Bootstrap estimates must be finite")
    if (result.ci_low > result.ci_high).any():
        raise ValueError("Bootstrap interval endpoints are reversed")
    if ((result[["p_value", "p_adjusted"]] < 0) | (result[["p_value", "p_adjusted"]] > 1)).any().any():
        raise ValueError("Bootstrap p-values must lie in [0,1]")
    for raw, percent in (("effect", "effect_pct"), ("ci_low", "ci_low_pct"), ("ci_high", "ci_high_pct")):
        expected = 100 * result[raw]
        if percent in result and not np.allclose(result[percent], expected, rtol=1e-10, atol=1e-12):
            raise ValueError("Bootstrap percent fields disagree with their raw ratios")
        result[percent] = expected
    result["candidate_history"] = result.candidate_history.astype(str)
    result["reference_history"] = result.reference_history.astype(str)
    primary = result.is_primary_block
    if not primary.isin([True, False]).all():
        raise ValueError("is_primary_block must be boolean")
    for weighting, rows in result.loc[primary].groupby("weighting"):
        if rows.block_length.nunique() != 1:
            raise ValueError(f"Part {part}/{weighting} must have one primary block setting")
    if "comparison_id" not in result:
        result["comparison_id"] = (result.comparison_kind.astype(str) + "__" + result.reference_policy.astype(str)
                                   + "__" + result.candidate_history)
    if result.duplicated(["weighting", "block_length", "comparison_id"]).any():
        raise ValueError("Duplicate bootstrap comparison cells")
    return result


def _save(figure, output, name, plt):
    figure.savefig(output / f"{name}.png", dpi=180, bbox_inches="tight")
    figure.savefig(output / f"{name}.pdf", bbox_inches="tight")
    plt.close(figure)


def _interval_panel(axis, rows, labels, title):
    """Draw endpoints directly: a skewed basic CI need not contain its estimate."""
    if len(rows) != len(labels) or rows.empty:
        raise ValueError(f"Missing prespecified comparisons for {title}")
    positions = np.arange(len(rows))
    colors = np.where(rows.effect_pct.to_numpy() >= 0, "#176d87", "#a84643")
    axis.hlines(positions, rows.ci_low_pct, rows.ci_high_pct, color=colors, linewidth=2)
    axis.scatter(rows.effect_pct, positions, c=colors, s=27, zorder=3)
    axis.set_yticks(positions, labels)
    axis.invert_yaxis()
    axis.axvline(0, color="#333333", linewidth=0.8)
    axis.set_title(title)
    axis.grid(axis="x", alpha=0.2)
    for position, pvalue in zip(positions, rows.p_adjusted, strict=True):
        axis.text(1.02, position, f"pH={pvalue:.4f}", transform=axis.get_yaxis_transform(),
                  va="center", fontsize=8)


def _ordered_comparisons(frame, weighting, kind, references=None, histories=None):
    rows = frame.loc[(frame.weighting == weighting) & (frame.comparison_kind == kind)
                     & frame.is_primary_block].copy()
    if references is not None:
        rows = rows.set_index("reference_policy").reindex(references).reset_index()
    if histories is not None:
        rows = rows.set_index("candidate_history").reindex(histories).reset_index()
    if rows[["effect_pct", "ci_low_pct", "ci_high_pct", "p_adjusted"]].isna().any().any():
        raise ValueError("A prespecified bootstrap contrast is missing")
    return rows


def write_reports(development, final, part_a_bootstrap, part_b_bootstrap, output: Path) -> dict:
    """Write complete tables and six PNG/PDF figure pairs without reselection."""
    if set(development.stage) != {"development"} or set(final.stage) != {"final"}:
        raise ValueError("Development and final inputs must retain their declared stages")
    per_target, aggregate = summarize_history(pd.concat([development, final], ignore_index=True))
    part_a, part_b = _bootstrap_frame(part_a_bootstrap, "A"), _bootstrap_frame(part_b_bootstrap, "B")
    histories = _history_order(aggregate.history)
    finite = [label for label in histories if label != "expanding"]
    weightings = [label for label in ("value", "equal") if label in set(aggregate.weighting)]
    if weightings != ["value", "equal"]:
        raise ValueError("Reports require primary value and robustness equal weightings")
    required_policies = {FACTOR_POLICY, *REFERENCES}
    if not required_policies.issubset(set(aggregate.policy_id)):
        raise ValueError("A fixed factor or direct reference policy is missing")
    output = Path(output)
    files = ["target_summary.csv", "aggregate_summary.csv", "part_a_inference.csv", "part_b_inference.csv", "report_manifest.json"]
    figure_files = [f"{name}.{extension}" for name in FIGURE_NAMES for extension in ("png", "pdf")]
    if any((output / name).exists() for name in files + figure_files):
        raise FileExistsError("Report artifacts already exist; use a new directory")
    output.mkdir(parents=True, exist_ok=True)
    per_target.to_csv(output / files[0], index=False, lineterminator="\n")
    aggregate.to_csv(output / files[1], index=False, lineterminator="\n")
    part_a.to_csv(output / files[2], index=False, lineterminator="\n")
    part_b.to_csv(output / files[3], index=False, lineterminator="\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with plt.rc_context({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False}):
        figure, axes = plt.subplots(1, 2, figsize=(12, 4.2))
        for axis, weighting in zip(axes, weightings, strict=True):
            rows = _ordered_comparisons(part_a, weighting, "factor_vs_reference", references=REFERENCES)
            _interval_panel(axis, rows, REFERENCE_LABELS, f"{weighting}-weighted | Holm family 4")
            axis.set_xlabel("Factor improvement relative to named reference (%)")
        figure.suptitle("Part A: exploratory inference on seen 2022–2024 forecasts\nMarginal 95% basic intervals; one-sided Holm p-values (pH); primary block length 13")
        figure.tight_layout(rect=(0, 0, 0.97, 0.87), w_pad=6)
        _save(figure, output, FIGURE_NAMES[0], plt)

        figure, axes = plt.subplots(2, 4, figsize=(18, 7), squeeze=False)
        for row, weighting in enumerate(weightings):
            for column, (reference, label) in enumerate(zip(REFERENCES, REFERENCE_LABELS, strict=True)):
                subset = part_b.loc[part_b.reference_policy == reference]
                rows = _ordered_comparisons(subset, weighting, "factor_vs_reference", histories=histories)
                _interval_panel(axes[row, column], rows, histories, f"{weighting} | vs {label}")
                axes[row, column].set_xlabel("Improvement relative to reference (%)")
        figure.suptitle("Part B: fixed factor versus matching-history references\nMarginal 95% basic intervals; pH adjusted jointly over all 19 contrasts per weighting; block 13")
        figure.tight_layout(rect=(0, 0, 0.98, 0.91), w_pad=5)
        _save(figure, output, FIGURE_NAMES[1], plt)

        figure, axes = plt.subplots(1, 2, figsize=(12, 4.2))
        for axis, weighting in zip(axes, weightings, strict=True):
            rows = _ordered_comparisons(part_b, weighting, "history_vs_expanding", histories=finite)
            _interval_panel(axis, rows, [f"L={label} vs expanding" for label in finite], f"{weighting}-weighted | Holm family 19")
            axis.set_xlabel("Finite-history factor improvement vs expanding factor (%)")
        figure.suptitle("Part B: direct coefficient-history comparisons\nSame all-48 common-slope policy and expanding PCA; marginal 95% basic intervals; block 13")
        figure.tight_layout(rect=(0, 0, 0.97, 0.87), w_pad=6)
        _save(figure, output, FIGURE_NAMES[2], plt)

        figure, axes = plt.subplots(2, 2, figsize=(12, 8), squeeze=False)
        policy_labels = [(FACTOR_POLICY, "Fixed common-slope factor"), *zip(REFERENCES, REFERENCE_LABELS)]
        for row, stage in enumerate(("development", "final")):
            for column, weighting in enumerate(weightings):
                axis = axes[row, column]
                cell = aggregate.loc[(aggregate.stage == stage) & (aggregate.weighting == weighting)]
                for policy, label in policy_labels:
                    values = cell.loc[cell.policy_id == policy].set_index("history").reindex(histories)
                    axis.plot(range(len(histories)), values.improvement_pct, marker="o", label=label,
                              linestyle="--" if policy == REFERENCES[0] else "-")
                axis.set_xticks(range(len(histories)), histories)
                axis.set_title(f"{stage.capitalize()} | {weighting}-weighted")
                axis.set_xlabel("Supervised coefficient-history pairs")
                axis.set_ylabel("Improvement vs matching own-history model (%)")
                axis.grid(alpha=0.2)
        handles, labels = axes[0, 0].get_legend_handles_labels()
        figure.legend(handles, labels, loc="lower center", ncol=3)
        figure.suptitle("All four history rules and fixed direct references\nEqual-target mean MSE ratios; descriptive curves, no new winner selection")
        figure.tight_layout(rect=(0, 0.08, 1, 0.92))
        _save(figure, output, FIGURE_NAMES[3], plt)

        targets = [name for name in S if name in set(per_target.target)]
        targets += sorted(set(per_target.target).difference(targets))
        selected = per_target.loc[(per_target.stage == "final") & (per_target.policy_id == FACTOR_POLICY)]
        limit = max(float(selected.improvement_pct.abs().max()), 1.0)
        figure, axes = plt.subplots(1, 2, figsize=(12, 5), squeeze=False)
        for column, weighting in enumerate(weightings):
            table = selected.loc[selected.weighting == weighting].pivot(index="target", columns="history", values="improvement_pct").reindex(index=targets, columns=histories)
            values = table.to_numpy()
            artist = axes[0, column].imshow(values, cmap="RdYlGn", vmin=-limit, vmax=limit, aspect="auto")
            axes[0, column].set_xticks(range(len(histories)), histories)
            axes[0, column].set_yticks(range(len(targets)), targets)
            axes[0, column].set_title(f"Final | {weighting}-weighted")
            axes[0, column].set_xlabel("Coefficient-history pairs")
            for i in range(len(targets)):
                for j in range(len(histories)):
                    axes[0, column].text(j, i, f"{values[i,j]:.1f}", ha="center", va="center")
            figure.colorbar(artist, ax=axes[0, column], label="Improvement vs matching own history (%)", shrink=0.8)
        figure.suptitle("Every target and history for the fixed common-slope factor\nPoint estimates; adverse targets retained; no target-specific policy selection")
        figure.tight_layout(rect=(0, 0, 1, 0.9))
        _save(figure, output, FIGURE_NAMES[4], plt)

        figure, axes = plt.subplots(2, 2, figsize=(16, 11), squeeze=False,
                                    gridspec_kw={"height_ratios": [1, 3.4]})
        for row, (part, table) in enumerate((("A", part_a), ("B", part_b))):
            for column, weighting in enumerate(weightings):
                cell = table.loc[table.weighting == weighting]
                order = cell.loc[cell.is_primary_block, "comparison_id"].tolist()
                matrix = cell.pivot(index="comparison_id", columns="block_length", values="p_adjusted").reindex(order)
                if matrix.isna().any().any():
                    raise ValueError("Block sensitivity must retain every comparison for every block setting")
                labels = []
                for comparison in order:
                    item = cell.loc[cell.comparison_id == comparison].iloc[0]
                    reference = ("expanding factor" if item.comparison_kind == "history_vs_expanding" else
                                 REFERENCE_LABELS[REFERENCES.index(item.reference_policy)])
                    labels.append(f"L={item.candidate_history} vs {reference}")
                axis = axes[row, column]
                artist = axis.imshow(matrix.to_numpy(), cmap="viridis_r", vmin=0, vmax=1, aspect="auto")
                axis.set_yticks(range(len(labels)), labels, fontsize=8)
                axis.set_xticks(range(len(matrix.columns)), [str(value) for value in matrix.columns])
                axis.set_xlabel("Expected stationary block length (dates)")
                axis.set_title(f"Part {part} | {weighting} | Holm family {4 if part == 'A' else 19}")
                for i in range(len(matrix)):
                    for j in range(len(matrix.columns)):
                        axis.text(j, i, f"{matrix.iloc[i,j]:.4f}", ha="center", va="center", fontsize=8)
                figure.colorbar(artist, ax=axis, label="One-sided Holm-adjusted p", shrink=0.7)
        figure.suptitle("Every prespecified comparison and block-length setting\nPart A exploratory; Part B approximate frozen-procedure inference; no minimum-p selection")
        figure.tight_layout(rect=(0, 0, 1, 0.95))
        _save(figure, output, FIGURE_NAMES[5], plt)

    manifest = dict(
        factor_policy=FACTOR_POLICY, no_new_winner_selection=True,
        histories=histories, target_rows=len(per_target), aggregate_rows=len(aggregate),
        part_a_inference_rows=len(part_a), part_b_inference_rows=len(part_b),
        intervals="marginal 95% basic bootstrap; not simultaneous confidence intervals",
        pvalues="one-sided Holm adjustment: 4 contrasts in A, 19 in B; separate weight/block families",
        persistence="same forecast repeated across history labels; not independent evidence",
        tables=files[:4], figures=figure_files,
    )
    (output / files[4]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dict(target_summary=files[0], aggregate_summary=files[1], part_a_bootstrap=files[2],
                part_b_bootstrap=files[3], manifest=files[4], figures=figure_files)
