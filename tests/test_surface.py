"""Exact-objective and chronological/storage checks for Experiment 3."""

from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from factorcast.features import ForecastDataset
from factorcast.models import FactorForecaster, PCARepresentation
from factorcast.surface import (
    FactorWindow, LocalWindow, PrefixRepresentation, TARGETS,
    _CSVShards, cell_inventory, run_stage,
)


ROOT = Path(__file__).resolve().parents[1]


def _config():
    config = tomllib.loads((ROOT / "configs" / "experiment_03_plan.toml").read_text(encoding="utf-8"))
    config["grid"]["finite_coefficient_pairs"] = [18, 26]
    config["grid"]["factor_counts"] = [1, 2, 8]
    config["calendar"].update(first_outer_cutoff_pairs=34, validation_pairs=8, refit_every_pairs=5,
                              earlier_seen_response_end="2000-09-22", later_seen_response_start="2000-09-29",
                              later_seen_response_end="2000-10-27")
    return config


def _dataset(n=42, seed=39, zero_outcomes=False):
    rng = np.random.default_rng(seed)
    factors = np.empty((n + 13, 3))
    factors[0] = rng.normal(size=3)
    for t in range(1, len(factors)):
        factors[t] = 0.7 * factors[t - 1] + rng.normal(size=3)
    raw = factors @ rng.normal(size=(3, 48)) + rng.normal(scale=0.7, size=(n + 13, 48))
    x = raw[11:11 + n]
    y = np.zeros_like(x) if zero_outcomes else raw[12:12 + n]
    local = np.stack([x, np.array([raw[t - 3:t + 1].mean(axis=0) for t in range(11, 11 + n)]),
                      np.array([raw[t - 11:t + 1].mean(axis=0) for t in range(11, 11 + n)])], axis=2)
    origins = pd.date_range("2000-01-07", periods=n, freq="W-FRI")
    names = TARGETS + tuple(f"Industry{i}" for i in range(42))
    return ForecastDataset(x, y, local[:, 0], local, origins, origins + pd.Timedelta(days=7), names, "Food", {})


class SurfaceModelTests(unittest.TestCase):
    def test_exact_schur_partial_matches_frozen_stacked_solver_all_K_and_penalties(self):
        dataset = _dataset(n=70)
        representation = PCARepresentation(8).fit(dataset.X[:52])
        local = LocalWindow(dataset.Y[:52], dataset.local_all[:52])
        window = FactorWindow(local, representation.transform(dataset.X[:52]))
        for k in (1, 2, 8):
            prefix = PrefixRepresentation(representation, k)
            self.assertEqual(prefix.transform(dataset.X[:5]).shape, (5, k))
            for penalty in (0.01, 0.1, 1.0, 10.0, 100.0):
                with self.subTest(k=k, penalty=penalty):
                    original = FactorForecaster(k, pooling="partial", penalty=penalty, representation=prefix).fit(
                        dataset.X[:52], dataset.Y[:52], local=dataset.local_all[:52])
                    fast = window.partial(k, penalty)
                    self.assertEqual(fast.slopes.shape, (k, 48))
                    np.testing.assert_allclose(fast.slopes, original.slopes_, rtol=2e-8, atol=2e-10)
                    predictions = fast.predict_scores(prefix.transform(dataset.X[52:]), dataset.local_all[52:])
                    np.testing.assert_allclose(predictions, original.predict_all(dataset.X[52:], dataset.local_all[52:]),
                                               rtol=2e-8, atol=2e-10)
                    gradients = np.einsum("jkl,lj->jk", window.grams[:, :k, :k], fast.slopes)
                    gradients += penalty * (fast.slopes.T - fast.slopes.mean(axis=1))
                    np.testing.assert_allclose(gradients, window.rhs[:, :k], rtol=1e-8, atol=1e-10)

    def test_separate_common_prefix_width_and_old_gram_solver_compatibility(self):
        dataset = _dataset(n=65)
        representation = PCARepresentation(8).fit(dataset.X[:52])
        window = FactorWindow(LocalWindow(dataset.Y[:52], dataset.local_all[:52]),
                              representation.transform(dataset.X[:52]))
        predictions = {}
        for k in (1, 2, 8):
            prefix = PrefixRepresentation(representation, k)
            for sharing in ("separate", "pooled"):
                original = FactorForecaster(k, pooling=sharing, representation=prefix).fit(
                    dataset.X[:52], dataset.Y[:52], local=dataset.local_all[:52])
                fast = window.separate(k) if sharing == "separate" else window.common(k)
                value = fast.predict_scores(prefix.transform(dataset.X[52:]), dataset.local_all[52:])
                np.testing.assert_allclose(value, original.predict_all(dataset.X[52:], dataset.local_all[52:]),
                                           rtol=1e-9, atol=1e-10)
                predictions[(k, sharing)] = value
        self.assertFalse(np.allclose(predictions[(1, "separate")], predictions[(8, "separate")]))
        with self.assertRaisesRegex(ValueError, "width"):
            window.common(2).predict_scores(representation.transform(dataset.X[52:]), dataset.local_all[52:])
        with self.assertRaises(RuntimeError):
            PrefixRepresentation(representation, 2).fit(dataset.X)

    def test_gram_common_rank_deficiency_matches_existing_behavior(self):
        rng = np.random.default_rng(17)
        z = rng.normal(size=(45, 2))
        z[:, 1] = z[:, 0]
        y = rng.normal(size=(45, 48))
        local = rng.normal(size=(45, 48, 3))
        fitted = FactorWindow(LocalWindow(y, local), z)
        common = fitted.common(2)
        expected = np.linalg.lstsq(fitted.grams.sum(axis=0), fitted.rhs.sum(axis=0), rcond=None)[0]
        np.testing.assert_allclose(common.slopes, np.repeat(expected[:, None], 48, axis=1))
        # A separate target's coefficients cannot borrow another outcome.
        changed = y.copy()
        changed[:, 1:] += 1000 * rng.normal(size=(45, 47))
        original_target = fitted.separate(2, (0,))
        changed_target = FactorWindow(LocalWindow(changed, local), z).separate(2, (0,))
        np.testing.assert_array_equal(original_target.slopes, changed_target.slopes)


class SurfaceRunnerTests(unittest.TestCase):
    def test_full_canonical_inventory_counts_and_deduplication(self):
        plan = tomllib.loads((ROOT / "configs" / "experiment_03_plan.toml").read_text(encoding="utf-8"))
        cells = cell_inventory(plan)
        self.assertEqual(len(cells), 956)
        self.assertEqual(sum(cells.sharing == "own"), 20)
        self.assertEqual(sum((cells["mode"] == "shared") & (cells.history == "expanding")), 24)
        self.assertEqual(sum(cells["mode"].isin(["matched", "expanding"])), 912)
        self.assertTrue(cells.cell_id.is_unique)
        np.testing.assert_array_equal(cells.cell_index, np.arange(956))

    def test_streamed_forecast_and_tuning_records_match_memmaps_and_windows(self):
        dataset = _dataset()
        config = _config()
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            output = Path(temporary) / "earlier"
            observed_windows = []
            from factorcast import surface
            original = surface._pca

            def record_window(data, start, stop, components):
                observed_windows.append((start, stop, components))
                return original(data, start, stop, components)

            with patch("factorcast.surface._pca", side_effect=record_window):
                manifest = run_stage({"value": dataset}, config, "earlier_seen", output)
            cells = pd.read_csv(output / "cells.csv", dtype={"history": str})
            dates = json.loads((output / "dates.json").read_text())
            self.assertEqual(dates["origin_indices"], [34, 35, 36])
            self.assertEqual(dates["refit_indices"], [34, 34, 34])
            self.assertEqual(len(observed_windows), len(set(observed_windows)))
            self.assertEqual(set(observed_windows), {(8, 26, 8), (16, 34, 8), (0, 26, 8), (8, 34, 8), (0, 34, 8)})
            self.assertEqual(manifest["timing"]["pca_fits"], 5)
            predictions = np.load(output / "predictions_value.npy", mmap_mode="r")
            actual = np.load(output / "actual_value.npy", mmap_mode="r")
            self.assertEqual(predictions.shape, (3, len(cells), 6))
            self.assertEqual(manifest["timing"]["prediction_rows"], 3 * len(cells) * 6)
            read_rows = 0
            for item in manifest["file_records"]:
                path = output / item["path"]
                self.assertLess(item["bytes"], 83886080)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
                records = pd.read_csv(path, dtype={"history": str})
                self.assertEqual(len(records), item["rows"])
                if item["path"].startswith("predictions/"):
                    read_rows += len(records)
                    for row in records.itertuples(index=False):
                        self.assertAlmostEqual(row.prediction, predictions[row.date_index, row.cell_index, row.target_index])
                        self.assertAlmostEqual(row.actual, actual[row.date_index, row.target_index])
                        self.assertAlmostEqual(row.squared_error, (row.prediction - row.actual) ** 2)
                        self.assertEqual(row.target, TARGETS[row.target_index])
                else:
                    for row in records.itertuples(index=False):
                        if row.sharing == "own":
                            self.assertTrue(pd.isna(row.inner_pca_start))
                            continue
                        length = None if row.history == "expanding" else int(row.history)
                        self.assertEqual(row.inner_coef_stop, 26)
                        self.assertEqual(row.outer_coef_stop, 34)
                        self.assertEqual(row.inner_coef_start, 0 if length is None else 26 - length)
                        self.assertEqual(row.outer_coef_start, 0 if length is None else 34 - length)
                        self.assertEqual(row.inner_pca_start, row.inner_coef_start if row.mode == "matched" else 0)
                        self.assertEqual(row.outer_pca_start, row.outer_coef_start if row.mode == "matched" else 0)
                        self.assertEqual(row.computed_components, 8)
                        self.assertEqual(row.used_components, row.K)
            self.assertEqual(read_rows, manifest["timing"]["prediction_rows"])
            for path, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((output / path).read_bytes()).hexdigest(), digest)
            self.assertNotIn("stage_manifest.json", manifest["files"])
            predictions._mmap.close()
            actual._mmap.close()

    def test_boundary_replay_future_outcome_invariance_and_first_penalty_tie(self):
        config = _config()
        dataset = _dataset(zero_outcomes=True)
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            earlier = Path(temporary) / "earlier"
            later = Path(temporary) / "later"
            changed_output = Path(temporary) / "changed"
            run_stage({"value": dataset}, config, "earlier_seen", earlier)
            run_stage({"value": dataset}, config, "later_seen", later)
            dates = json.loads((later / "dates.json").read_text())
            self.assertEqual(dates["origin_indices"], [37, 38, 39, 40, 41])
            self.assertEqual(dates["refit_indices"], [34, 34, 39, 39, 39])
            changed_y = dataset.Y.copy()
            changed_y[34:] = 10000
            changed_x = dataset.X.copy()
            changed_x[37:] *= 100
            changed = replace(dataset, Y=changed_y, X=changed_x)
            run_stage({"value": changed}, config, "earlier_seen", changed_output)
            np.testing.assert_array_equal(np.load(earlier / "predictions_value.npy"),
                                          np.load(changed_output / "predictions_value.npy"))
            for path in earlier.glob("tuning/value/*/*/*.csv.gz"):
                table = pd.read_csv(path)
                selected = table[(table.sharing == "partial") & table.chosen]
                self.assertTrue((selected.candidate_penalty == 0.01).all())
                self.assertTrue((selected.chosen_penalty == 0.01).all())
            # Actual validation and choice records replay identically at cut34.
            first_later = pd.concat([pd.read_csv(path) for path in later.glob("tuning/value/*/*/*.csv.gz")])
            first_later = first_later[first_later.refit_index == 34].sort_values(["cell_index", "target", "candidate_penalty"])
            first_earlier = pd.concat([pd.read_csv(path) for path in earlier.glob("tuning/value/*/*/*.csv.gz")]).sort_values(
                ["cell_index", "target", "candidate_penalty"])
            pd.testing.assert_frame_equal(first_later.drop(columns="stage").reset_index(drop=True),
                                          first_earlier.drop(columns="stage").reset_index(drop=True))

    def test_deterministic_shards_split_bounded_records_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            roots = [Path(temporary) / "one", Path(temporary) / "two"]
            reports = []
            for root in roots:
                writer = _CSVShards(root, "predictions", ["a", "b"], 1024)
                writer.append(("value", "matched", "52"), [(i, "longfield" * 10) for i in range(30)])
                reports.append(writer.close())
            self.assertGreater(len(reports[0]), 1)
            self.assertEqual(sum(item["rows"] for item in reports[0]), 30)
            self.assertEqual(reports[0], reports[1])
            for item in reports[0]:
                self.assertLess(item["bytes"], 1024)
                with gzip.open(roots[0] / item["path"], "rt") as source:
                    self.assertEqual(source.readline().strip(), "a,b")
            occupied = Path(temporary) / "occupied"
            occupied.mkdir()
            (occupied / "artifact.txt").write_text("existing")
            with self.assertRaises(FileExistsError):
                run_stage({"value": _dataset()}, _config(), "earlier_seen", occupied)


if __name__ == "__main__":
    unittest.main()
