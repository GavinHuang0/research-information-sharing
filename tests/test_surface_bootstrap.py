"""Synthetic algorithm controls, not finite-sample calibration evidence."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from factorcast.bootstrap import stationary_indices
from factorcast.surface_bootstrap import (
    FINITE_HISTORIES, HISTORIES, SHARING_RULES, index_fingerprint, run_inference,
)


def cell_fixture():
    rows = []

    def add(mode, history, sharing, k):
        rows.append({
            "cell_index": len(rows), "cell_id": f"{mode}_{history}_{sharing}_{k}",
            "mode": mode, "history": history, "sharing": sharing, "K": k,
            "n_factors": k, "n_measurements": 0 if sharing == "own" else 48,
            "n_outcomes": 48 if sharing in ("common", "partial") else 1,
        })

    for history in HISTORIES:
        add("none", history, "own", 0)
    for mode in ("matched", "expanding"):
        for history in FINITE_HISTORIES:
            for k in range(1, 9):
                for sharing in SHARING_RULES:
                    add(mode, history, sharing, k)
    for k in range(1, 9):
        for sharing in SHARING_RULES:
            add("shared", "expanding", sharing, k)
    return pd.DataFrame(rows)


def synthetic_inputs(period="later_seen", n_dates=8):
    cells = cell_fixture()
    rng = np.random.Generator(np.random.PCG64(1142))
    # Nonproportional target/date/cell variation detects incorrect pooled MSEs,
    # fixed denominators, contrast signs, and independently resampled cells.
    losses = np.exp(rng.normal(scale=0.6, size=(n_dates, len(cells), 6)))
    dates = pd.date_range("2025-01-03" if period == "later_seen" else "2020-01-03", periods=n_dates, freq="W-FRI")
    return {"value": losses, "equal": losses * 2}, cells, dates


def config(replicates=17, blocks=(13,)):
    return {"bootstrap": {"replicates": replicates, "seed": 20261102,
                          "expected_block_length_dates": blocks[0],
                          "sensitivity_block_lengths_dates": list(blocks[1:])}}


def scalar_statistics(losses, cells, row, indices):
    lookup = dict(zip(cells.cell_id, cells.cell_index))
    c, r, d = (lookup[row[column]] for column in ("candidate_cell_id", "reference_cell_id", "denominator_cell_id"))

    def statistic(values):
        means = values.mean(axis=0)
        if row["kind"] == "own_gain":
            return 1 - sum(means[c, i] / means[d, i] for i in range(6)) / 6
        return sum((means[r, i] - means[c, i]) / means[d, i] for i in range(6)) / 6

    observed = statistic(losses)
    bootstrap = np.array([statistic(losses[draw]) for draw in indices])
    low, high = np.quantile(bootstrap, [.025, .975], method="linear")
    count = sum(value - observed >= observed for value in bootstrap)
    return observed, 2 * observed - high, 2 * observed - low, (1 + count) / (len(indices) + 1)


class SurfaceBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.losses, cls.cells, cls.dates = synthetic_inputs()
        cls.settings = config(31, (13, 6, 26))
        with patch("factorcast.surface_bootstrap.stationary_indices", wraps=stationary_indices) as generator:
            cls.results, cls.manifest = run_inference(cls.losses, cls.cells, cls.dates, cls.settings)
        cls.generator_call_count = generator.call_count

    def test_exact_all_grid_counts_and_anchor_family_membership(self):
        frame = self.results
        self.assertEqual(len(frame), 2016 * 2 * 3)
        self.assertEqual(self.generator_call_count, 3)
        for _, group in frame.groupby(["weighting", "block_length"]):
            self.assertEqual(group.kind.value_counts().to_dict(), {
                "own_gain": 936, "pooling_difference": 624, "mode_difference": 456})
            anchors = group[group.anchor]
            self.assertEqual(len(anchors), 30)
            self.assertEqual(anchors.kind.value_counts().to_dict(), {"own_gain": 21, "mode_difference": 9})
            self.assertTrue((anchors.K == 2).all())
            self.assertEqual(set(anchors.history), {"104", "260", "520", "expanding"})
            self.assertEqual(sum(anchors.history == "expanding"), 3)
            self.assertTrue((anchors.family_size == 30).all())
            self.assertEqual(anchors.family_id.nunique(), 1)
        nonanchors = frame[~frame.anchor]
        self.assertTrue(nonanchors[["p_value", "p_adjusted", "tail_count", "reject_adjusted"]].isna().all().all())

    def test_all_anchors_holm_together_match_independent_step_down(self):
        for _, family in self.results[self.results.anchor].groupby("family_id"):
            order = np.argsort(family.p_value.to_numpy(), kind="stable")
            expected = np.empty(30)
            running_max = 0.
            pvalues = family.p_value.to_numpy()
            for rank, position in enumerate(order):
                running_max = max(running_max, (30 - rank) * pvalues[position])
                expected[position] = min(1., running_max)
            np.testing.assert_allclose(family.p_adjusted.to_numpy(), expected, rtol=0, atol=0)
            np.testing.assert_array_equal(family.reject_adjusted.to_numpy(),
                                          (family.effect.to_numpy() > 0) & (expected < .05))

    def test_scalar_oracle_for_gain_mode_and_pooling_recomputes_denominators(self):
        frame = self.results[(self.results.weighting == "value") & (self.results.block_length == 13)]
        indices = stationary_indices(len(self.dates), 31, 13, 20261102)
        examples = [
            frame[(frame.kind == "own_gain") & (frame.history == "104") & (frame.K == 2)].iloc[0],
            frame[(frame.kind == "mode_difference") & (frame.history == "260") & (frame.K == 2)].iloc[0],
            frame[(frame.kind == "pooling_difference") & (frame.history == "52") & (frame.K == 7)].iloc[0],
            frame[(frame.kind == "pooling_difference") & (frame.history == "expanding")].iloc[0],
        ]
        for row in examples:
            with self.subTest(kind=row.kind, history=row.history):
                expected = scalar_statistics(self.losses["value"], self.cells, row, indices)
                np.testing.assert_allclose([row.effect, row.ci_low, row.ci_high], expected[:3], rtol=1e-12, atol=1e-12)
                if row.anchor:
                    self.assertEqual(row.p_value, expected[3])
                self.assertAlmostEqual(row.effect_pct, row.effect * 100)
        mode = examples[1]
        own = frame[frame.kind == "own_gain"].set_index("candidate_cell_id")
        self.assertAlmostEqual(mode.effect, own.loc[mode.candidate_cell_id].effect - own.loc[mode.reference_cell_id].effect)
        pooling = examples[2]
        self.assertAlmostEqual(pooling.effect, own.loc[pooling.candidate_cell_id].effect - own.loc[pooling.reference_cell_id].effect)

    def test_common_indices_exact_hash_and_scaled_weightings_paired(self):
        for block, group in self.results.groupby("block_length"):
            matrix = stationary_indices(len(self.dates), 31, block, 20261102)
            raw = np.asarray(matrix.shape, dtype="<i8").tobytes() + np.asarray(matrix, dtype="<i8").tobytes()
            expected = hashlib.sha256(raw).hexdigest()
            self.assertEqual(index_fingerprint(matrix), expected)
            self.assertEqual(self.manifest["matrices"][str(block)]["sha256"], expected)
            self.assertEqual(group.index_sha256.nunique(), 1)
        value = self.results[self.results.weighting == "value"].reset_index(drop=True)
        equal = self.results[self.results.weighting == "equal"].reset_index(drop=True)
        for column in ("effect", "ci_low", "ci_high", "p_value", "p_adjusted"):
            np.testing.assert_allclose(value[column], equal[column], rtol=0, atol=0, equal_nan=True)
        self.assertTrue(self.manifest["one_shared_matrix_across_weightings_targets_all_cells_contrasts"])

    def test_adjusted_p_equal_alpha_does_not_cross_strict_frozen_threshold(self):
        losses, cells, dates = synthetic_inputs(n_dates=2)
        with patch("factorcast.surface_bootstrap.holm_adjust", return_value=np.full(30, .05)):
            frame, manifest = run_inference(losses, cells, dates, config(3))
        anchors = frame[frame.anchor]
        self.assertTrue((anchors.p_adjusted == .05).all())
        self.assertTrue((anchors.effect > 0).any())
        self.assertFalse(anchors.reject_adjusted.any())
        self.assertIn("strictly less than alpha", manifest["rejection_rule"])

    def test_earlier_period_has_no_formal_pvalues_or_anchor_rows(self):
        losses, cells, dates = synthetic_inputs("earlier_seen", 3)
        frame, manifest = run_inference(losses, cells.sample(frac=1, random_state=3), dates, config(5), "earlier_seen")
        self.assertEqual(len(frame), 4032)
        self.assertFalse(frame.anchor.any())
        self.assertTrue(frame[["p_value", "p_adjusted", "tail_count"]].isna().all().all())
        self.assertEqual(manifest["anchor_family_size"], 0)

    def test_all_zero_null_ties_unfavorable_and_interval_not_clipped(self):
        losses, cells, dates = synthetic_inputs(n_dates=2)
        # Every factor is identical to own: all contrasts zero, p=1 incl ties.
        losses = {key: np.ones_like(value) for key, value in losses.items()}
        frame, _ = run_inference(losses, cells, dates, config(5))
        self.assertTrue((frame.effect == 0).all())
        self.assertTrue((frame.ci_low == 0).all())
        self.assertTrue((frame[frame.anchor].p_value == 1).all())
        self.assertTrue((frame[frame.anchor].tail_count == 5).all())
        # Explicit resamples include only either date or both.  Reference is
        # [1,.1], candidate[0,1]; the basic interval can exceed gain bound1.
        own = cells.index[(cells.sharing == "own") & (cells.history == "104")][0]
        factor = cells.index[(cells["mode"] == "matched") & (cells.history == "104") & (cells.K == 2) & (cells.sharing == "separate")][0]
        unfavorable = cells.index[(cells["mode"] == "matched") & (cells.history == "104") & (cells.K == 2) & (cells.sharing == "common")][0]
        for value in losses.values():
            value[:, own, :] = np.array([1, .1])[:, None]
            value[:, factor, :] = np.array([0, 1])[:, None]
            value[:, unfavorable, :] = 2 * value[:, own, :]
        indices = np.array([[0, 0], [1, 1], [0, 1]])
        with patch("factorcast.surface_bootstrap.stationary_indices", return_value=indices):
            frame, _ = run_inference(losses, cells, dates, config(3))
        row = frame[(frame.weighting == "value") & (frame.kind == "own_gain") & (frame.candidate_cell_id == cells.loc[factor, "cell_id"])].iloc[0]
        self.assertGreater(row.ci_high, 1)
        self.assertEqual(row.p_value, scalar_statistics(losses["value"], cells, row, indices)[3])
        negative = frame[(frame.weighting == "value") & (frame.kind == "own_gain") & (frame.candidate_cell_id == cells.loc[unfavorable, "cell_id"])].iloc[0]
        self.assertEqual(negative.effect, -1)
        self.assertEqual(negative.p_value, 1)

    def test_invalid_inventory_losses_settings_and_dates_abort(self):
        losses, cells, dates = synthetic_inputs(n_dates=2)
        bad_cells = cells.copy()
        bad_cells.loc[20, "K"] = 8
        cases = [
            (losses, cells.iloc[:-1], dates, config()),
            (losses, bad_cells, dates, config()),
            ({"value": losses["value"]}, cells, dates, config()),
            ({"value": losses["value"][:, :, :5], "equal": losses["equal"]}, cells, dates, config()),
            (losses, cells, dates[::-1], config()),
            (losses, cells, dates + pd.Timedelta(days=1), config()),
            (losses, cells, dates, config(0)),
            (losses, cells, dates, config(3, (13, 13))),
        ]
        for arguments in cases:
            with self.subTest(case=len(arguments)), self.assertRaises(ValueError):
                run_inference(*arguments)
        for invalid in (np.nan, np.inf, -1):
            changed = {key: value.copy() for key, value in losses.items()}
            changed["value"][0, 950, 0] = invalid
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "finite and nonnegative"):
                run_inference(changed, cells, dates, config())
        bad_meta = cells.copy()
        bad_meta.loc[20, "n_factors"] = 8
        with self.assertRaisesRegex(ValueError, "n_factors"):
            run_inference(losses, bad_meta, dates, config())
        with self.assertRaisesRegex(ValueError, "outside earlier_seen"):
            run_inference(losses, cells, dates, config(), "earlier_seen")

    def test_original_and_resampled_zero_denominator_abort_without_dropping(self):
        losses, cells, dates = synthetic_inputs(n_dates=2)
        own = cells.index[(cells.sharing == "own") & (cells.history == "52")][0]
        changed = {key: value.copy() for key, value in losses.items()}
        changed["value"][:, own, 0] = 0
        with self.assertRaisesRegex(ValueError, "Original own-history denominator"):
            run_inference(changed, cells, dates, config())
        changed["value"][1, own, 0] = 1
        indices = np.array([[0, 0], [1, 1]])
        with patch("factorcast.surface_bootstrap.stationary_indices", return_value=indices):
            with self.assertRaisesRegex(ValueError, "draw 0, target Food"):
                run_inference(changed, cells, dates, config(2))

    def test_history_sized_mean_batches_and_optional_archives_no_overwrite(self):
        losses, cells, dates = synthetic_inputs(n_dates=3)
        from factorcast import surface_bootstrap
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            output = Path(temporary)
            with patch("factorcast.surface_bootstrap._means_for_history", wraps=surface_bootstrap._means_for_history) as means:
                frame, manifest = run_inference(losses, cells, dates, config(5), output=output)
            widths = [len(call.args[1]) for call in means.call_args_list]
            self.assertEqual(max(widths), 49)
            self.assertEqual(min(widths), 25)
            self.assertEqual(len(widths), 40)
            self.assertEqual(len(pd.read_csv(output / "bootstrap_results.csv")), len(frame))
            self.assertEqual(len(pd.read_csv(output / "anchor_table.csv")), 60)
            self.assertEqual(json.loads((output / "bootstrap_index_manifest.json").read_bytes()), manifest)
            entry = manifest["matrices"]["13"]
            with np.load(output / entry["file"], allow_pickle=False) as archive:
                np.testing.assert_array_equal(archive["indices"], stationary_indices(3, 5, 13, 20261102))
            self.assertEqual(hashlib.sha256((output / entry["file"]).read_bytes()).hexdigest(), entry["file_sha256"])
            for name in ("bootstrap_results.csv", "anchor_table.csv", "bootstrap_index_manifest.json"):
                self.assertNotIn(b"\r", (output / name).read_bytes())
            with self.assertRaises(FileExistsError):
                run_inference(losses, cells, dates, config(5), output=output)


if __name__ == "__main__":
    unittest.main()
