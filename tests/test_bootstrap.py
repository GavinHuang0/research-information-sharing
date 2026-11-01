"""Numerical, chronology and synthetic controls for saved-loss inference.

These tests check the declared algorithm.  They do not calibrate the complete
forecast fitting/tuning pipeline or prove finite-sample bootstrap coverage.
"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from factorcast.bootstrap import (
    FACTOR_POLICY, HISTORIES, REFERENCE_POLICIES, TARGETS,
    compare_loss_arrays, holm_adjust, run_inference, stationary_indices,
)


def prediction_fixture(part="A"):
    histories = ("expanding",) if part == "A" else HISTORIES
    dates = pd.date_range("2022-01-07" if part == "A" else "2025-01-03", periods=8, freq="W-FRI")
    rows = []
    factors = {"104": 0.5, "260": 0.6, "520": 0.7, "expanding": 0.8}
    policies = (FACTOR_POLICY, *REFERENCE_POLICIES)
    for weighting in ("value", "equal"):
        for history in histories:
            for policy in policies:
                multiplier = factors[history] if policy == FACTOR_POLICY else 1.0 + 0.1 * REFERENCE_POLICIES.index(policy)
                for target_index, target in enumerate(TARGETS):
                    for date_index, response in enumerate(dates):
                        loss = (date_index + 1) * (target_index + 1) * multiplier
                        if weighting == "equal":
                            loss *= 2
                        rows.append({
                            "weighting": weighting, "history": history, "policy_id": policy,
                            "target": target, "origin_date": response - pd.Timedelta(days=7),
                            "response_date": response, "stage": "final", "actual": 0.0,
                            "prediction": np.sqrt(loss), "squared_error": loss,
                        })
    return pd.DataFrame(rows)


def small_config():
    return {"inference": {"replicates": 31, "expected_block_length_dates": 13,
                          "sensitivity_block_lengths_dates": [6, 26], "seed": 20261031}}


def repeated_targets(rows):
    return np.repeat(np.asarray(rows, dtype=float)[:, None], 6, axis=1)


class StationaryIndexTests(unittest.TestCase):
    def test_exact_rng_draw_order_matches_independent_tiny_oracle(self):
        expected = np.array([[3, 0, 1, 2], [0, 1, 1, 2], [0, 3, 1, 1]], dtype=np.int64)
        np.testing.assert_array_equal(stationary_indices(4, 3, 2, 7), expected)
        rng = np.random.Generator(np.random.PCG64(412))
        oracle = []
        for _ in range(7):
            row = [int(rng.integers(5))]
            while len(row) < 5:
                restart = rng.random() < 1 / 3
                row.append(int(rng.integers(5)) if restart else (row[-1] + 1) % 5)
            oracle.append(row)
        np.testing.assert_array_equal(stationary_indices(5, 7, 3, 412), np.array(oracle))

    def test_reproducible_int64_bounded_indices_and_single_date(self):
        first = stationary_indices(9, 21, 1, 17)
        self.assertEqual(first.dtype, np.dtype("int64"))
        np.testing.assert_array_equal(first, stationary_indices(9, 21, 1, 17))
        self.assertTrue(((first >= 0) & (first < 9)).all())
        np.testing.assert_array_equal(stationary_indices(1, 3, 26, 9), np.zeros((3, 1), dtype=np.int64))

    def test_invalid_rng_arguments_rejected(self):
        for args in ((0, 3, 2, 1), (4, 0, 2, 1), (4, 3, 0.5, 1),
                     (4, 3, np.nan, 1), (True, 3, 2, 1), (4, 3, 2, -1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                stationary_indices(*args)


class LossComparisonTests(unittest.TestCase):
    def test_ratio_denominators_null_root_and_basic_interval_hand_calculation(self):
        # Ghat=1-1/2=1/2.  Bootstrap G is [0,2/3,1/2], not
        # [1/2,1/2,1/2] from erroneously fixing the original denominator.
        indices = np.array([[0, 0], [1, 1], [0, 1]])
        result = compare_loss_arrays(repeated_targets([1, 1]), repeated_targets([1, 3]), indices)
        self.assertAlmostEqual(result["effect"], 0.5)
        self.assertAlmostEqual(result["bootstrap_min"], 0)
        self.assertAlmostEqual(result["bootstrap_max"], 2 / 3)
        self.assertEqual(result["tail_count"], 0)
        self.assertAlmostEqual(result["p_value"], 1 / 4)
        self.assertAlmostEqual(result["ci_low"], 1 - (0.95 * 2 / 3 + 0.05 * 0.5))
        self.assertAlmostEqual(result["ci_high"], 0.975)

    def test_ties_and_positive_negative_constant_ratio_controls(self):
        indices = np.array([[0, 0, 0], [2, 2, 2], [0, 1, 2], [1, 0, 1]])
        reference = repeated_targets([1, 2, 3])
        null = compare_loss_arrays(reference, reference, indices)
        self.assertEqual(null["effect"], 0)
        self.assertEqual(null["tail_count"], 4)
        self.assertEqual(null["p_value"], 1)
        self.assertTrue(null["bootstrap_degenerate"])
        positive = compare_loss_arrays(reference / 2, reference, indices)
        self.assertEqual(positive["effect"], 0.5)
        self.assertEqual(positive["p_value"], 0.2)
        self.assertEqual(positive["ci_low"], 0.5)
        self.assertEqual(positive["ci_high"], 0.5)
        negative = compare_loss_arrays(reference * 2, reference, indices)
        self.assertEqual(negative["effect"], -1)
        self.assertEqual(negative["p_value"], 1)

    def test_targets_share_draws_and_are_averaged_after_individual_ratios(self):
        factor = np.array([[1, 9, 2, 7, 3, 6], [4, 2, 8, 1, 9, 3]], dtype=float)
        reference = np.array([[1, 2, 3, 4, 5, 6], [20, 7, 6, 5, 4, 3]], dtype=float)
        indices = np.array([[0, 0], [1, 1], [1, 0]])
        expected = 1 - np.mean(factor.mean(axis=0) / reference.mean(axis=0))
        sample = [1 - np.mean(factor[row].mean(axis=0) / reference[row].mean(axis=0)) for row in indices]
        result = compare_loss_arrays(factor, reference, indices)
        self.assertAlmostEqual(result["effect"], expected)
        self.assertAlmostEqual(result["bootstrap_min"], min(sample))
        self.assertAlmostEqual(result["bootstrap_max"], max(sample))
        self.assertNotAlmostEqual(expected, 1 - factor.mean() / reference.mean())

    def test_original_or_single_draw_zero_denominator_aborts(self):
        candidate = repeated_targets([1, 1])
        with self.assertRaisesRegex(ValueError, "Original reference denominator"):
            compare_loss_arrays(candidate, np.zeros_like(candidate), np.array([[0, 1]]))
        with self.assertRaisesRegex(ValueError, "draw 0"):
            compare_loss_arrays(candidate, repeated_targets([0, 1]), np.array([[0, 0], [1, 1]]))

    def test_basic_interval_is_not_clipped_to_parameter_bound(self):
        result = compare_loss_arrays(repeated_targets([0, 1]), repeated_targets([1, 0.1]),
                                     np.array([[0, 0], [1, 1], [0, 1]]))
        # Basic interval inversion can exceed G's upper parameter bound of 1.
        self.assertGreater(result["ci_high"], 1)

    def test_invalid_losses_and_indices_rejected(self):
        good = repeated_targets([1, 2])
        for invalid in (np.full_like(good, np.nan), -good, good[:, :5]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                compare_loss_arrays(invalid, good, np.array([[0, 1]]))
        for invalid in (np.array([[0.0, 1.0]]), np.array([[0, 2]]), np.array([0, 1]), np.array([[0]])):
            with self.subTest(indices=invalid), self.assertRaises(ValueError):
                compare_loss_arrays(good, good, invalid)

    def test_stationary_dependent_loss_null_and_positive_effect_controls(self):
        # Stationary AR(1) starts from its invariant Gaussian distribution.
        # This checks known directions, not bootstrap coverage or test size.
        rng = np.random.Generator(np.random.PCG64(944))
        rho = 0.7
        state = np.empty(240)
        state[0] = rng.normal(scale=1 / np.sqrt(1 - rho ** 2))
        for t in range(1, len(state)):
            state[t] = rho * state[t - 1] + rng.normal()
        reference = np.exp(0.3 * state[:, None] + rng.normal(scale=0.15, size=(240, 6)))
        factor = reference * (0.65 + 0.05 * np.tanh(state[:, None]))
        indices = stationary_indices(240, 299, 13, 118)
        null = compare_loss_arrays(reference, reference, indices)
        self.assertEqual(null["p_value"], 1)
        # A lagged copy has the same stationary mean loss but different
        # per-date losses, providing a nondegenerate known-null control.
        lagged_null = compare_loss_arrays(np.roll(reference, 1, axis=0), reference, indices)
        self.assertGreater(lagged_null["bootstrap_max"], lagged_null["bootstrap_min"])
        self.assertLess(lagged_null["ci_low"], 0)
        self.assertGreater(lagged_null["ci_high"], 0)
        self.assertGreater(lagged_null["p_value"], 0.05)
        # Independent equal-law model shocks give an equal-marginal-mean null
        # with genuinely different candidate/reference losses on each date.
        model_shocks = np.empty((240, 2))
        model_shocks[0] = rng.normal(scale=0.2 / np.sqrt(1 - 0.4 ** 2), size=2)
        for t in range(1, 240):
            model_shocks[t] = 0.4 * model_shocks[t - 1] + rng.normal(scale=0.2, size=2)
        paired_candidate = reference * np.exp(model_shocks[:, [0]])
        paired_reference = reference * np.exp(model_shocks[:, [1]])
        exchangeable = compare_loss_arrays(paired_candidate, paired_reference, indices)
        shifted = compare_loss_arrays(paired_candidate * np.exp(-0.2), paired_reference, indices)
        self.assertGreater(exchangeable["bootstrap_max"], exchangeable["bootstrap_min"])
        self.assertGreater(shifted["effect"], exchangeable["effect"])
        self.assertLessEqual(shifted["p_value"], exchangeable["p_value"])
        # Independent scalar loop checks the nondegenerate null-root tail.
        observed = 1 - np.mean(paired_candidate.mean(axis=0) / paired_reference.mean(axis=0))
        draws = np.array([1 - np.mean(paired_candidate[row].mean(axis=0)
                                    / paired_reference[row].mean(axis=0)) for row in indices])
        expected_p = (1 + sum(value - observed >= observed for value in draws)) / (len(draws) + 1)
        self.assertEqual(exchangeable["p_value"], expected_p)
        favorable = compare_loss_arrays(factor, reference, indices)
        unfavorable = compare_loss_arrays(reference * 1.2, reference, indices)
        self.assertGreater(favorable["effect"], 0)
        self.assertGreater(favorable["ci_low"], 0)
        self.assertLess(favorable["p_value"], 0.05)
        self.assertLess(unfavorable["effect"], 0)
        self.assertEqual(unfavorable["p_value"], 1)


class HolmTests(unittest.TestCase):
    def test_exact_step_down_reordering_and_ties(self):
        np.testing.assert_allclose(holm_adjust([0.04, 0.01, 0.03, 0.2]), [0.09, 0.04, 0.09, 0.2])
        np.testing.assert_allclose(holm_adjust([0.01, 0.01, 0.9]), [0.03, 0.03, 0.9])
        np.testing.assert_allclose(holm_adjust([0, 1]), [0, 1])

    def test_invalid_pvalues_rejected(self):
        for values in ([], [[0.1]], [np.nan], [-0.1], [1.1]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                holm_adjust(values)


class InferenceTests(unittest.TestCase):
    def test_part_a_four_families_share_one_matrix_across_weights(self):
        frame = prediction_fixture().drop(columns="history")
        with patch("factorcast.bootstrap.stationary_indices", wraps=stationary_indices) as generator:
            results, manifest = run_inference(frame, "A", small_config())
        self.assertEqual(generator.call_count, 3)
        self.assertEqual(len(results), 4 * 2 * 3)
        self.assertTrue((results.family_size == 4).all())
        self.assertTrue((results.n_targets == 6).all())
        self.assertEqual(manifest["target_order"], list(TARGETS))
        for block, group in results.groupby("block_length"):
            self.assertEqual(group.index_sha256.nunique(), 1)
            matrix = stationary_indices(8, 31, block, 20261031)
            raw = np.asarray(matrix.shape, dtype="<i8").tobytes() + np.asarray(matrix, dtype="<i8").tobytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest["matrices"][str(block)]["sha256"])
        original = results[results.weighting == "value"].sort_values(["block_length", "comparison_id"])
        robust = results[results.weighting == "equal"].sort_values(["block_length", "comparison_id"])
        np.testing.assert_allclose(original.effect, robust.effect)

    def test_part_b_nineteen_comparisons_and_direct_history_tests(self):
        results, manifest = run_inference(prediction_fixture("B"), "B", small_config())
        self.assertEqual(len(results), 19 * 2 * 3)
        self.assertTrue((results.family_size == 19).all())
        for _, family in results.groupby("family_id"):
            self.assertEqual(len(family), 19)
            np.testing.assert_allclose(family.p_adjusted, holm_adjust(family.p_value))
            self.assertEqual(sum(family.comparison_kind == "history_vs_expanding"), 3)
        history = results[(results.weighting == "value") & (results.block_length == 13)
                          & (results.comparison_kind == "history_vs_expanding")
                          & (results.candidate_history == "104")].iloc[0]
        self.assertAlmostEqual(history.effect, 1 - 0.5 / 0.8)
        self.assertEqual(history.reference_history, "expanding")
        self.assertEqual(history.reference_policy, FACTOR_POLICY)
        self.assertEqual(manifest["n_dates"], 8)

    def test_canonical_date_order_is_reproducible_after_row_permutation(self):
        frame = prediction_fixture()
        first, first_manifest = run_inference(frame, "A", small_config())
        shuffled, second_manifest = run_inference(frame.sample(frac=1, random_state=19), "A", small_config())
        pd.testing.assert_frame_equal(first, shuffled)
        self.assertEqual(first_manifest, second_manifest)

    def test_invalid_dates_actuals_losses_and_missing_cells_rejected(self):
        frame = prediction_fixture("B")
        with self.assertRaisesRegex(ValueError, "identical eligible date order"):
            run_inference(frame.drop(index=0), "B", small_config())
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            run_inference(pd.concat([frame, frame.iloc[[0]]]), "B", small_config())
        missing = frame[~((frame.history == "104") & (frame.policy_id == REFERENCE_POLICIES[0]))]
        with self.assertRaisesRegex(ValueError, "same policies"):
            run_inference(missing, "B", small_config())
        wrong = frame.copy()
        wrong.loc[0, "actual"] = 1
        with self.assertRaisesRegex(ValueError, "Stored squared errors"):
            run_inference(wrong, "B", small_config())
        with self.assertRaisesRegex(ValueError, "Actual outcomes"):
            run_inference(wrong.drop(columns="squared_error"), "B", small_config())

    def test_development_does_not_enter_part_b_inference(self):
        frame = prediction_fixture("B")
        development = frame.copy()
        development["stage"] = "development"
        development["prediction"] = 1000
        development["squared_error"] = 1000000
        combined, _ = run_inference(pd.concat([frame, development]), "B", small_config())
        standalone, _ = run_inference(frame, "B", small_config())
        pd.testing.assert_frame_equal(combined, standalone)
        with self.assertRaisesRegex(ValueError, "final-stage"):
            run_inference(development, "B", small_config())

    def test_optional_output_preserves_exact_indices_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            output = Path(temporary)
            results, manifest = run_inference(prediction_fixture(), "A", small_config(), output)
            self.assertEqual(len(pd.read_csv(output / "inference.csv")), len(results))
            self.assertEqual(json.loads((output / "bootstrap_index_manifest.json").read_text()), manifest)
            for block, entry in manifest["matrices"].items():
                with np.load(output / entry["file"], allow_pickle=False) as saved:
                    np.testing.assert_array_equal(saved["indices"], stationary_indices(8, 31, int(block), 20261031))
                self.assertEqual(hashlib.sha256((output / entry["file"]).read_bytes()).hexdigest(), entry["file_sha256"])
            with self.assertRaises(FileExistsError):
                run_inference(prediction_fixture(), "A", small_config(), output)


if __name__ == "__main__":
    unittest.main()
