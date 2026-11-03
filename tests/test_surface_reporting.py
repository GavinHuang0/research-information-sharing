"""Synthetic memmap summaries and figures; no empirical forecasts/inference."""

from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from factorcast import surface_reporting as reporting

TARGETS = ["Food", "Mach", "Banks", "Oil", "Util", "Hlth"]


def configuration(full=False):
    return dict(
        design=dict(targets=TARGETS, primary_weighting="value", robustness_weighting="equal"),
        grid=dict(finite_coefficient_pairs=list(range(52, 521, 26)) if full else [104, 260, 520],
                  factor_counts=list(range(1, 9)) if full else [1, 2]),
        bootstrap=dict(expected_block_length_dates=13, sensitivity_block_lengths_dates=[6, 26]),
        execution=dict(report_cell_batch_size=3),
    )


def inventory(config):
    rows = []

    def add(mode, history, sharing, k):
        history = str(history)
        own = sharing == "own"
        rows.append(dict(
            cell_index=len(rows), cell_id=f"local_history__L-{history}" if own else
            f"factor_{sharing}__PCA-{mode}__L-{history}__K-{k}",
            mode=mode, history=history, sharing=sharing, K=k, n_factors=k,
            n_measurements=0 if own else 48, n_outcomes=1 if sharing in ("own", "separate") else 48,
            method="local_history" if own else f"factor_{sharing}",
        ))

    for history in [*config["grid"]["finite_coefficient_pairs"], "expanding"]:
        add("none", history, "own", 0)
    for mode in reporting.MODES:
        for history in config["grid"]["finite_coefficient_pairs"]:
            for k in config["grid"]["factor_counts"]:
                for sharing in reporting.RULES:
                    add(mode, history, sharing, k)
    for k in config["grid"]["factor_counts"]:
        for sharing in reporting.RULES:
            add("shared", "expanding", sharing, k)
    return pd.DataFrame(rows)


def write_stage(root, period, config):
    path = root / period
    path.mkdir()
    cells = inventory(config)
    cells.to_csv(path / "cells.csv", index=False)
    origins = pd.date_range("2020-01-03" if period == "earlier_seen" else "2025-01-03", periods=3, freq="W-FRI")
    metadata = dict(stage=period, target_order=TARGETS, origin_indices=[572, 573, 574],
                    refit_indices=[572] * 3, origin_dates=origins.strftime("%Y-%m-%d").tolist(),
                    response_dates=(origins + pd.Timedelta(days=7)).strftime("%Y-%m-%d").tolist(), n_dates=3)
    (path / "dates.json").write_text(json.dumps(metadata))
    for weighting in ("value", "equal"):
        actual = np.zeros((3, 6))
        prediction = np.empty((3, len(cells), 6))
        for row in cells.to_dict("records"):
            history_scale = 1.2 if row["history"] == "expanding" else 1.4 - 0.0003 * int(row["history"])
            base = np.arange(1, 7)[None, :] * np.array([0.9, 1.0, 1.1])[:, None] * history_scale
            ratio = np.ones(6)
            if row["sharing"] != "own":
                ratio[:] = 0.87 + 0.02 * row["K"] + (0.03 if row["mode"] == "matched" else 0)
                ratio[2] += 0.15  # Preserve adverse Banks cells.
                ratio *= {"separate": 1.0, "common": 0.98, "partial": 0.97}[row["sharing"]]
            prediction[:, row["cell_index"], :] = base * ratio * (1.1 if weighting == "equal" else 1)
        np.save(path / f"predictions_{weighting}.npy", prediction)
        np.save(path / f"actual_{weighting}.npy", actual)
    return path, cells


def inference_fixture(root, config):
    rows = []
    for period in reporting.PERIODS:
        _, aggregate = reporting.summarize_from_stage(root / period, config)
        for weighting in ("value", "equal"):
            cell = aggregate.loc[aggregate.weighting == weighting]
            own_ids = cell.loc[cell.sharing == "own"].set_index("history").cell_id.to_dict()
            factors = cell.loc[cell.sharing != "own"]
            lookup = cell.set_index("cell_id")
            comparisons = []

            def add(kind, candidate, reference, effect, mode):
                item = dict(kind=kind, candidate_cell_id=candidate["cell_id"], reference_cell_id=reference,
                            denominator_cell_id=own_ids[candidate["history"]], mode=mode,
                            history=candidate["history"], sharing=candidate["sharing"], K=candidate["K"], effect=effect)
                item["comparison_id"] = f"{kind}__{candidate['cell_id']}"
                comparisons.append(item)

            for item in factors.to_dict("records"):
                add("own_gain", item, own_ids[item["history"]], item["improvement_pct"] / 100, item["mode"])
                if item["mode"] == "expanding":
                    reference = item["cell_id"].replace("PCA-expanding", "PCA-matched")
                    add("mode_difference", item, reference,
                        (item["improvement_pct"] - lookup.loc[reference, "improvement_pct"]) / 100,
                        "expanding-minus-matched")
                if item["sharing"] in ("common", "partial"):
                    reference = item["cell_id"].replace(f"factor_{item['sharing']}", "factor_separate")
                    add("pooling_difference", item, reference,
                        (item["improvement_pct"] - lookup.loc[reference, "improvement_pct"]) / 100, item["mode"])
            for block in (13, 6, 26):
                for index, comparison in enumerate(comparisons):
                    effect = comparison["effect"]
                    anchor = period == "later_seen" and comparison["K"] == 2 and comparison["kind"] != "pooling_difference"
                    low, high = effect - 0.04, effect + 0.05
                    if index == 0:
                        low, high = effect - 0.04, effect - 0.01  # Basic CI can exclude its own estimate.
                    rows.append(dict(
                        **comparison, period=period, weighting=weighting, block_length=block,
                        ci_low=low, ci_high=high, effect_pct=100 * effect, ci_low_pct=100 * low, ci_high_pct=100 * high,
                        anchor=anchor, p_value=0.25 if anchor else np.nan, p_adjusted=1.0 if anchor else np.nan,
                    ))
    frame = pd.DataFrame(rows)
    directory = root / "inference"
    directory.mkdir()
    frame.to_csv(directory / "bootstrap_results.csv", index=False)
    frame.loc[frame.anchor].to_csv(directory / "anchor_table.csv", index=False)
    return frame


class SurfaceReportingTests(unittest.TestCase):
    def test_full_inventory_counts_and_equal_target_ratio_definition(self):
        config = configuration(full=True)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            root = Path(temporary)
            target_parts, aggregates = [], []
            for period in reporting.PERIODS:
                directory, cells = write_stage(root, period, config)
                self.assertEqual(len(cells), 956)
                target, aggregate = reporting.summarize_from_stage(directory, config)
                target_parts.append(target)
                aggregates.append(aggregate)
                self.assertEqual(len(target), 956 * 6 * 2)
                self.assertEqual(len(aggregate), 956 * 2)
                self.assertEqual(len(aggregate.loc[(aggregate.weighting == "value") & (aggregate.sharing == "own")]), 20)
            self.assertEqual(len(pd.concat(target_parts)), 22944)
            self.assertEqual(len(pd.concat(aggregates)), 3824)
            directory = root / "earlier_seen"
            own = int(cells.loc[(cells.sharing == "own") & (cells.history == "52"), "cell_index"].iloc[0])
            factor = int(cells.loc[(cells.sharing == "separate") & (cells["mode"] == "matched") &
                                   (cells.history == "52") & (cells.K == 1), "cell_index"].iloc[0])
            saved = np.load(directory / "predictions_value.npy", mmap_mode="r+")
            saved[:, own, :] = [1, 10, 1, 1, 1, 1]
            saved[:, factor, :] = [0.5, 12, 1, 1, 1, 1]
            saved.flush()
            del saved
            _, aggregate = reporting.summarize_from_stage(directory, config)
            selected = aggregate.loc[(aggregate.weighting == "value") & (aggregate.cell_index == factor)].iloc[0]
            self.assertAlmostEqual(selected.mean_ratio_mse, (0.25 + 1.44 + 4) / 6)
            self.assertGreater(selected.mean_mse / aggregate.loc[(aggregate.weighting == "value") & (aggregate.cell_index == own), "mean_mse"].iloc[0], 1)

    def test_prediction_loading_is_memmapped_and_cell_bounded(self):
        config = configuration()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            directory, _ = write_stage(Path(temporary), "earlier_seen", config)
            original_load = np.load
            slices = []

            class SliceOnly:
                def __init__(self, array):
                    self.array, self.shape = array, array.shape

                def __getitem__(self, key):
                    self_slice = key[1]
                    if not isinstance(self_slice, slice):
                        raise AssertionError("Prediction access must be a cell slice")
                    width = self_slice.stop - self_slice.start
                    if width > config["execution"]["report_cell_batch_size"]:
                        raise AssertionError("Prediction batch exceeded its bound")
                    slices.append(width)
                    return self.array[key]

            def load(path, **kwargs):
                self.assertEqual(kwargs["mmap_mode"], "r")
                array = original_load(path, **kwargs)
                self.assertIsInstance(array, np.memmap)
                return SliceOnly(array) if Path(path).name.startswith("predictions_") else array

            with patch.object(reporting.np, "load", side_effect=load):
                reporting.summarize_from_stage(directory, config)
            self.assertTrue(slices)
            self.assertLessEqual(max(slices), 3)

    def test_invalid_baseline_or_forecast_does_not_get_dropped(self):
        config = configuration()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            directory, _ = write_stage(Path(temporary), "earlier_seen", config)
            prediction = np.load(directory / "predictions_value.npy", mmap_mode="r+")
            prediction[:, 0, 0] = 0
            prediction.flush()
            with self.assertRaisesRegex(ValueError, "baseline loss must be positive"):
                reporting.summarize_from_stage(directory, config)
            prediction[:, 0, 0] = np.nan
            prediction.flush()
            with self.assertRaisesRegex(ValueError, "forecast must be finite"):
                reporting.summarize_from_stage(directory, config)
            del prediction

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib is optional")
    def test_all_surface_figures_controls_tables_and_anchors_render(self):
        config = configuration()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            root = Path(temporary)
            for period in reporting.PERIODS:
                write_stage(root, period, config)
            inference = inference_fixture(root, config)
            artifacts = reporting.write_reports(root, config)
            output = root / "reports"
            self.assertEqual(len(artifacts["figures"]), 38)
            for name in artifacts["figures"]:
                self.assertGreater((output / name).stat().st_size, 100)
            saved = pd.read_csv(output / artifacts["bootstrap_summary"])
            self.assertEqual(len(saved), len(inference))
            self.assertTrue(saved.p_value.isna().any())  # No fabricated p-values outside anchors.
            self.assertEqual(set(saved.block_length), {6, 13, 26})
            anchors = pd.read_csv(output / artifacts["anchor_table"])
            self.assertEqual(len(anchors), 180)
            self.assertEqual(set(anchors.period), {"later_seen"})
            manifest = json.loads((output / artifacts["manifest"]).read_text())
            self.assertIn("Deferred", manifest["calibration_power"])
            self.assertIn("not simultaneous", manifest["intervals"])
            self.assertIn("sidebands", manifest["controls"])
            with self.assertRaises(FileExistsError):
                reporting.write_reports(root, config)


if __name__ == "__main__":
    unittest.main()
