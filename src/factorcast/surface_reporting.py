"""Bounded-memory summaries and prespecified Experiment 3 surface figures.

Prediction files are read as NPY memory maps in cell batches. All surface
cells remain descriptive; only the saved anchor table carries Holm p-values.
Calibration and power remain deferred, and every period has already been seen.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd

PERIODS = ("earlier_seen", "later_seen")
MODES = ("matched", "expanding")
RULES = ("separate", "common", "partial")
WARNING = "Exploratory seen-period estimates; calibration/power deferred; no calibrated significance claim"
CELL_FIELDS = ["cell_index", "cell_id", "mode", "history", "sharing", "K", "n_factors",
               "n_measurements", "n_outcomes", "method"]


def _read_inventory(path):
    cells = pd.read_csv(path, dtype={"history": str})
    missing = set(CELL_FIELDS).difference(cells)
    if cells.empty or missing:
        raise ValueError(f"Cell inventory is empty or missing {sorted(missing)}")
    if cells[CELL_FIELDS].isna().any().any() or cells.cell_id.duplicated().any():
        raise ValueError("Canonical inventory fields must be unique and nonmissing")
    if not np.array_equal(cells.cell_index.to_numpy(), np.arange(len(cells))):
        raise ValueError("Cell indices must match the canonical NPY column order")
    if not cells.sharing.isin([*RULES, "own"]).all():
        raise ValueError("Unknown sharing rule")
    own = cells.loc[cells.sharing == "own"]
    if own.history.duplicated().any() or (own.K != 0).any():
        raise ValueError("Each history needs exactly one K=0 own reference")
    if set(cells.history) != set(own.history):
        raise ValueError("A matching-history own reference is missing")
    return cells


def summarize_from_stage(perioddir: Path, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize every cell/target with only a bounded prediction-cell batch."""
    perioddir = Path(perioddir)
    cells = _read_inventory(perioddir / "cells.csv")
    dates = json.loads((perioddir / "dates.json").read_bytes())
    period = dates["stage"]
    targets = list(config["design"]["targets"])
    if list(dates["target_order"]) != targets:
        raise ValueError("NPY target order differs from the declared target order")
    origins = pd.to_datetime(dates["origin_dates"], errors="raise")
    responses = pd.to_datetime(dates["response_dates"], errors="raise")
    n_dates = int(dates["n_dates"])
    if (n_dates < 1 or len(origins) != n_dates or len(responses) != n_dates
            or origins.has_duplicates or not origins.is_monotonic_increasing
            or not ((responses - origins) == pd.Timedelta(days=7)).all()):
        raise ValueError("Dates must be a nonempty chronological next-calendar-week sample")
    batch = config.get("execution", {}).get("report_cell_batch_size", 32)
    if not isinstance(batch, int) or isinstance(batch, bool) or batch < 1:
        raise ValueError("Report cell batch size must be a positive integer")
    own_indices = cells.loc[cells.sharing == "own"].set_index("history").cell_index.to_dict()
    target_rows, aggregate_rows = [], []
    for weighting in (config["design"]["primary_weighting"], config["design"]["robustness_weighting"]):
        prediction = np.load(perioddir / f"predictions_{weighting}.npy", mmap_mode="r", allow_pickle=False)
        actual = np.load(perioddir / f"actual_{weighting}.npy", mmap_mode="r", allow_pickle=False)
        if prediction.shape != (n_dates, len(cells), len(targets)) or actual.shape != (n_dates, len(targets)):
            raise ValueError("Prediction/actual NPY dimensions do not match metadata")
        if not np.isfinite(actual).all():
            raise ValueError("Realized responses must be finite")
        # Mean losses, not the full prediction grid, are retained in memory.
        means = np.empty((len(cells), len(targets)), dtype=float)
        absolutes = np.empty_like(means)
        for start in range(0, len(cells), batch):
            stop = min(start + batch, len(cells))
            values = prediction[:, start:stop, :]
            if not np.isfinite(values).all():
                raise ValueError("Every saved forecast must be finite")
            errors = values - actual[:, None, :]
            with np.errstate(over="ignore", invalid="ignore"):
                means[start:stop] = np.mean(errors * errors, axis=0)
                absolutes[start:stop] = np.mean(np.abs(errors), axis=0)
        if not np.isfinite(means).all() or not np.isfinite(absolutes).all():
            raise ValueError("Saved forecast losses must be finite")
        for cell in cells.to_dict("records"):
            index = cell["cell_index"]
            baseline_index = own_indices[cell["history"]]
            baseline_mse, baseline_mae = means[baseline_index], absolutes[baseline_index]
            if (baseline_mse <= 0).any() or (baseline_mae <= 0).any():
                raise ValueError("Matching-history baseline loss must be positive")
            ratio_mse, ratio_mae = means[index] / baseline_mse, absolutes[index] / baseline_mae
            common = dict(period=period, weighting=weighting, **cell)
            for target_index, target in enumerate(targets):
                target_rows.append(dict(
                    **common, target=target, n_forecasts=n_dates,
                    mse=float(means[index, target_index]), mae=float(absolutes[index, target_index]),
                    baseline_mse=float(baseline_mse[target_index]), baseline_mae=float(baseline_mae[target_index]),
                    ratio_mse=float(ratio_mse[target_index]), ratio_mae=float(ratio_mae[target_index]),
                    improvement_pct=float(100 * (1 - ratio_mse[target_index])),
                ))
            aggregate_rows.append(dict(
                **common, n_targets=len(targets), n_forecasts_per_target=n_dates,
                mean_mse=float(means[index].mean()), mean_mae=float(absolutes[index].mean()),
                mean_ratio_mse=float(ratio_mse.mean()), mean_ratio_mae=float(ratio_mae.mean()),
                improvement_pct=float(100 * (1 - ratio_mse.mean())),
                mae_improvement_pct=float(100 * (1 - ratio_mae.mean())),
            ))
        del prediction, actual
    return pd.DataFrame(target_rows), pd.DataFrame(aggregate_rows)


def _inference(path):
    frame = pd.read_csv(path, dtype={"history": str})
    required = {"period", "weighting", "kind", "comparison_id", "candidate_cell_id", "reference_cell_id",
                "denominator_cell_id", "mode", "history", "sharing", "K", "block_length", "effect", "ci_low", "ci_high"}
    if frame.empty or not required.issubset(frame):
        raise ValueError("Incomplete surface inference table")
    for column in ("effect", "ci_low", "ci_high"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not np.isfinite(frame[column]).all():
            raise ValueError("Inference effects and marginal intervals must be finite")
        percent = f"{column}_pct"
        if percent in frame and not np.allclose(frame[percent], 100 * frame[column], rtol=1e-10, atol=1e-12):
            raise ValueError("Inference percent fields disagree with their raw effects")
        frame[percent] = 100 * frame[column]
    if (frame.ci_low > frame.ci_high).any():
        raise ValueError("Marginal interval endpoints are reversed")
    if frame.duplicated(["period", "weighting", "block_length", "comparison_id"]).any():
        raise ValueError("Duplicate surface comparison rows")
    return frame


def _text_color(value, norm, cmap):
    red, green, blue, _ = cmap(norm(value))
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "white" if luminance < 0.46 else "black"


def _map(axis, values, histories, ks, title, norm, cmap, fmt=".1f"):
    values = np.asarray(values, dtype=float)
    if values.shape != (len(ks), len(histories)) or not np.isfinite(values).all():
        raise ValueError(f"Incomplete map: {title}")
    artist = axis.imshow(values, norm=norm, cmap=cmap, aspect="auto", origin="lower")
    axis.set_xticks(range(len(histories)), histories, rotation=90 if len(histories) > 3 else 0, fontsize=8)
    axis.set_yticks(range(len(ks)), ks)
    axis.set_xlabel("Coefficient-history pairs")
    axis.set_ylabel("PC count K")
    axis.set_title(title, fontsize=10)
    for row in range(len(ks)):
        for column in range(len(histories)):
            axis.text(column, row, format(values[row, column], fmt), ha="center", va="center", fontsize=6.5,
                      color=_text_color(values[row, column], norm, cmap))
    return artist


def _table_values(frame, field, histories, ks):
    if frame.duplicated(["history", "K"]).any():
        raise ValueError("Multiple cells occupy one surface coordinate")
    return frame.pivot(index="K", columns="history", values=field).reindex(index=ks, columns=histories).to_numpy()


def _save(figure, output, name, plt):
    figure.savefig(output / f"{name}.png", dpi=180, bbox_inches="tight")
    figure.savefig(output / f"{name}.pdf", bbox_inches="tight")
    plt.close(figure)
    return [f"{name}.png", f"{name}.pdf"]


def _gain_or_mse(cell, period, weighting, histories, ks, field, output, plt):
    from matplotlib.colors import Normalize, TwoSlopeNorm
    factors = cell.loc[cell.sharing != "own"]
    is_gain = field == "improvement_pct"
    values = factors[field].to_numpy()
    if is_gain:
        limit = max(float(np.abs(values).max()), 1.0)
        norm, cmap = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit), plt.get_cmap("RdBu")
    else:
        lower, upper = float(values.min()), float(values.max())
        norm, cmap = Normalize(vmin=min(0, lower), vmax=max(upper, 1e-12)), plt.get_cmap("cividis")
    figure = plt.figure(figsize=(21, 11 if is_gain else 13), layout="constrained")
    grid = figure.add_gridspec(3 if is_gain else 4, 3, width_ratios=[len(histories), len(histories), 2],
                              height_ratios=[1, 1, 1] if is_gain else [1, 1, 1, 0.7])
    axes = []
    for row, sharing in enumerate(RULES):
        for column, mode in enumerate(MODES):
            axis = figure.add_subplot(grid[row, column])
            selected = factors.loc[(factors.sharing == sharing) & (factors["mode"] == mode)]
            artist = _map(axis, _table_values(selected, field, histories, ks), histories, ks,
                          f"{sharing.capitalize()} | {'A: matched PCA' if mode == 'matched' else 'B: expanding PCA'}", norm, cmap,
                          ".1f" if is_gain else ".3f")
            axes.append(axis)
        axis = figure.add_subplot(grid[row, 2])
        selected = factors.loc[(factors.sharing == sharing) & (factors["mode"] == "shared")]
        _map(axis, _table_values(selected, field, ["expanding"], ks), ["Exp"], ks,
             "Shared control", norm, cmap, ".1f" if is_gain else ".3f")
        axes.append(axis)
    label = "Own-history-reference gain (%)" if is_gain else "Mean target MSE (squared log units)"
    figure.colorbar(artist, ax=axes, label=label, shrink=0.8)
    if not is_gain:
        own = cell.loc[cell.sharing == "own"].set_index("history")
        own_low, own_high = float(own.mean_mse.min()), float(own.mean_mse.max())
        own_pad = max((own_high - own_low) * 0.1, own_high * 0.02, 1e-12)
        own_limits = (max(0, own_low - own_pad), own_high + own_pad)
        axis = figure.add_subplot(grid[3, :2])
        axis.plot(range(len(histories)), own.reindex(histories).mean_mse, marker="o", color="#444444")
        axis.set_xticks(range(len(histories)), histories, rotation=90, fontsize=8)
        axis.set_title("K=0 own-history baseline: one reference per L, shared across modes/rules")
        axis.set_xlabel("Coefficient-history pairs")
        axis.set_ylabel("Mean target MSE")
        axis.set_ylim(*own_limits)
        axis.grid(alpha=0.2)
        axis = figure.add_subplot(grid[3, 2])
        axis.scatter([0], [own.loc["expanding", "mean_mse"]], color="#444444")
        axis.set_xticks([0], ["Exp"])
        axis.set_title("Own control", fontsize=9)
        axis.set_ylabel("MSE")
        axis.set_ylim(*own_limits)
        axis.grid(alpha=0.2)
    figure.suptitle(f"{period} | {weighting}-weighted | {'Gain' if is_gain else 'Absolute loss'} surfaces\n"
                   "Expanding controls are deduplicated sidebands, not finite coordinates\n" + WARNING, fontsize=12)
    return _save(figure, output, f"{period}_{weighting}_{'gain' if is_gain else 'absolute_mse'}", plt)


def _contrast_maps(frame, period, weighting, histories, ks, kind, output, plt):
    from matplotlib.colors import TwoSlopeNorm
    selected = frame.loc[(frame.period == period) & (frame.weighting == weighting) & (frame.kind == kind)]
    limit = max(float(selected.effect_pct.abs().max()), 1.0)
    norm, cmap = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit), plt.get_cmap("RdBu")
    if kind == "mode_difference":
        figure, axes = plt.subplots(1, 3, figsize=(23, 5.5), layout="constrained")
        for axis, sharing in zip(axes, RULES, strict=True):
            cell = selected.loc[selected.sharing == sharing]
            artist = _map(axis, _table_values(cell, "effect_pct", histories, ks), histories, ks,
                          f"{sharing.capitalize()} | expanding PCA minus matched PCA", norm, cmap)
        figure.colorbar(artist, ax=axes, label="Difference in own-reference gain (percentage points)", shrink=0.85)
        title = "PCA-mode contrasts: positive favors expanding PCA; common own-history denominator"
        name = "pca_mode_difference"
    else:
        figure = plt.figure(figsize=(21, 8), layout="constrained")
        grid = figure.add_gridspec(2, 3, width_ratios=[len(histories), len(histories), 2])
        axes = []
        for row, sharing in enumerate(("common", "partial")):
            for column, mode in enumerate(MODES):
                axis = figure.add_subplot(grid[row, column])
                cell = selected.loc[(selected.sharing == sharing) & (selected["mode"] == mode)]
                artist = _map(axis, _table_values(cell, "effect_pct", histories, ks), histories, ks,
                              f"{sharing.capitalize()} minus separate | {mode} PCA", norm, cmap)
                axes.append(axis)
            axis = figure.add_subplot(grid[row, 2])
            cell = selected.loc[(selected.sharing == sharing) & (selected["mode"] == "shared")]
            _map(axis, _table_values(cell, "effect_pct", ["expanding"], ks), ["Exp"], ks,
                 "Shared control", norm, cmap)
            axes.append(axis)
        figure.colorbar(artist, ax=axes, label="Difference in own-reference gain (percentage points)", shrink=0.85)
        title = "Pooling contrasts: positive favors named sharing rule; no formal interaction test"
        name = "pooling_difference"
    figure.suptitle(f"{period} | {weighting}-weighted\n{title}\n{WARNING}; no surface p-value stars", fontsize=11)
    return _save(figure, output, f"{period}_{weighting}_{name}", plt)


def _anchor_label(row):
    prefix = "Mode Delta" if row["kind"] == "mode_difference" else f"Own gain | {row['mode']}"
    return f"{prefix} | L={row['history']} | K={int(row['K'])} | {row['sharing']}"


def write_reports(runroot: Path, config: dict) -> dict:
    """Write all cells and contrasts; draw no selected-cell or significance map."""
    runroot = Path(runroot)
    targets, aggregates = [], []
    for period in PERIODS:
        target, aggregate = summarize_from_stage(runroot / period, config)
        targets.append(target)
        aggregates.append(aggregate)
    target = pd.concat(targets, ignore_index=True)
    aggregate = pd.concat(aggregates, ignore_index=True)
    inference = _inference(runroot / "inference/bootstrap_results.csv")
    anchors = _inference(runroot / "inference/anchor_table.csv")
    required_p = {"p_value", "p_adjusted"}
    if not required_p.issubset(anchors) or not np.isfinite(anchors[list(required_p)]).all().all():
        raise ValueError("Every anchor needs finite raw and Holm-adjusted p-values")
    if ((anchors[list(required_p)] < 0) | (anchors[list(required_p)] > 1)).any().any():
        raise ValueError("Anchor p-values must lie in [0,1]")
    if not (anchors.period == "later_seen").all():
        raise ValueError("Formal anchor p-values are confined to later_seen")
    primary_block = config["bootstrap"]["expected_block_length_dates"]
    primary = inference.loc[inference.block_length == primary_block]
    histories = [str(value) for value in config["grid"]["finite_coefficient_pairs"]]
    ks = list(config["grid"]["factor_counts"])
    output = runroot / "reports"
    tables = ["target_summary.csv", "aggregate_summary.csv", "bootstrap_summary.csv", "anchor_table.csv"]
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Surface reports already exist; use a new report directory")
    output.mkdir(parents=True, exist_ok=True)
    for frame, name in zip((target, aggregate, inference, anchors), tables, strict=True):
        frame.to_csv(output / name, index=False, float_format="%.17g", lineterminator="\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures = []
    with plt.rc_context({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False}):
        for period in PERIODS:
            for weighting in ("value", "equal"):
                cell = aggregate.loc[(aggregate.period == period) & (aggregate.weighting == weighting)]
                figures.extend(_gain_or_mse(cell, period, weighting, histories, ks, "improvement_pct", output, plt))
                figures.extend(_gain_or_mse(cell, period, weighting, histories, ks, "mean_mse", output, plt))
                for kind in ("mode_difference", "pooling_difference"):
                    figures.extend(_contrast_maps(primary, period, weighting, histories, ks, kind, output, plt))
        for weighting in ("value", "equal"):
            cell = anchors.loc[(anchors.weighting == weighting) & (anchors.block_length == primary_block)]
            if cell.empty:
                raise ValueError("A primary anchor family is missing")
            figure, axis = plt.subplots(figsize=(13, max(7, len(cell) * 0.34 + 2)), layout="constrained")
            positions = np.arange(len(cell))
            colors = np.where(cell.effect_pct.to_numpy() >= 0, "#176d87", "#a75e31")
            axis.hlines(positions, cell.ci_low_pct, cell.ci_high_pct, color=colors, linewidth=1.7)
            axis.scatter(cell.effect_pct, positions, c=colors, s=23, zorder=3)
            axis.set_yticks(positions, [_anchor_label(row) for row in cell.to_dict("records")], fontsize=8)
            axis.invert_yaxis()
            axis.axvline(0, color="#333333", linewidth=0.8)
            axis.set_xlabel("Own gain (%) or PCA-mode gain difference (percentage points), as labeled")
            for position, value in zip(positions, cell.p_adjusted, strict=True):
                axis.text(1.01, position, f"pH={value:.4f}", transform=axis.get_yaxis_transform(), va="center", fontsize=8)
            axis.grid(axis="x", alpha=0.2)
            axis.set_title(f"All declared later-seen anchors | {weighting}-weighted | block {primary_block}\n"
                           "Marginal nominal-95% basic intervals; one Holm-30 family\n" + WARNING, fontsize=11)
            figures.extend(_save(figure, output, f"later_seen_{weighting}_anchor_forest", plt))
        figure, axes = plt.subplots(1, 2, figsize=(18, 14), layout="constrained")
        for axis, weighting in zip(axes, ("value", "equal"), strict=True):
            cell = anchors.loc[anchors.weighting == weighting]
            order = cell.loc[cell.block_length == primary_block, "comparison_id"].tolist()
            matrix = cell.pivot(index="comparison_id", columns="block_length", values="p_adjusted").reindex(order)
            if matrix.isna().any().any():
                raise ValueError("Every block setting must retain every anchor")
            artist = axis.imshow(matrix.to_numpy(), cmap="cividis_r", vmin=0, vmax=1, aspect="auto")
            info = cell.drop_duplicates("comparison_id").set_index("comparison_id").reindex(order)
            axis.set_yticks(range(len(order)), [_anchor_label(row) for row in info.to_dict("records")], fontsize=7.5)
            axis.set_xticks(range(len(matrix.columns)), [str(value) for value in matrix.columns])
            axis.set_xlabel("Expected stationary block length (retained dates)")
            axis.set_title(f"{weighting}-weighted | separate Holm-30 family per block")
            for row in range(len(matrix)):
                for column in range(len(matrix.columns)):
                    value = matrix.iloc[row, column]
                    axis.text(column, row, f"{value:.4f}", ha="center", va="center", fontsize=8,
                              color=_text_color(value, artist.norm, artist.cmap))
            figure.colorbar(artist, ax=axis, label="One-sided Holm-adjusted p-value", shrink=0.7)
        figure.suptitle("All anchors and prescribed block settings; no minimum-p selection\n" + WARNING, fontsize=12)
        figures.extend(_save(figure, output, "later_seen_anchor_block_sensitivity", plt))
    manifest = dict(
        target_rows=len(target), aggregate_rows=len(aggregate), bootstrap_rows=len(inference), anchor_rows=len(anchors),
        primary_block=primary_block, figures=figures, tables=tables,
        prediction_loading="NPY mmap_mode=r; bounded cell batches; full prediction grid never copied",
        controls="Expanding coefficient controls are canonical sidebands; K=0 own references are not factor cells",
        intervals="Approximate nominal-95% basic marginal intervals; not simultaneous surface bands",
        pvalues="Only prespecified later_seen anchors; one Holm-30 family per weighting/block; no surface stars",
        calibration_power="Deferred and pending; Experiment2 adverse calibration findings remain applicable",
        interpretation="All periods already seen; exploratory; no winner recommendation or latent/trading claim",
    )
    (output / "report_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dict(target_summary=tables[0], aggregate_summary=tables[1], bootstrap_summary=tables[2],
                anchor_table=tables[3], manifest="report_manifest.json", figures=figures)
