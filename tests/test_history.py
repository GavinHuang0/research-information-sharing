"""Synthetic controls for finite supervised windows and expanding PCA."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from factorcast import history, pilot
from factorcast.features import ForecastDataset
from factorcast.models import PCARepresentation

NAMES = ("Other1", "Oil", "Hlth", "Banks", "Other2", "Food", "Mach", "Util")


def configuration():
    return dict(
        design=dict(targets=["Food"], small_panel=list(pilot.S), factor_count=2),
        part_b=dict(
            calendar=dict(first_outer_cutoff_pairs=20, refit_every_pairs=5,
                          development_response_end="2021-08-13", new_final_response_start="2021-08-14",
                          new_final_response_end="2022-12-31"),
            history=dict(finite_coefficient_pairs=[8, 12, 16], include_expanding_control=True, validation_pairs=4),
            tuning=dict(ridge_penalties=[0.01, 0.1], elasticnet_penalties=[0.001, 0.1],
                        pooling_penalties=[0.01, 1.0], elasticnet_l1_ratio=0.5,
                        elasticnet_tolerance=1e-10, elasticnet_max_iterations=100000),
        ),
    )


def dataset(rows=38):
    rng = np.random.default_rng(802)
    f = rng.normal(size=(rows + 1, 2))
    x = f @ rng.normal(size=(2, len(NAMES))) + rng.normal(scale=0.5, size=(rows + 1, len(NAMES)))
    local = np.stack([x[:-1], np.roll(x[:-1], 1, axis=0), np.roll(x[:-1], 2, axis=0)], axis=2)
    dates = pd.date_range("2021-01-01", periods=rows, freq="W-FRI")
    return ForecastDataset(
        X=x[:-1], Y=x[1:], local=local[:, NAMES.index("Food"), :], local_all=local,
        origin_dates=dates, response_dates=dates + pd.Timedelta(days=7),
        asset_names=NAMES, target_name="Food", report={},
    )


def fitted(policy, data, start, stop=20, pca_stop=20, cache=None):
    config = configuration()
    measurements, outcomes = history._members(policy, "Food", NAMES, pilot.S)
    fitted_model = history._fit_window(
        policy, 0.1, data, "Food", measurements, outcomes, start, stop, pca_stop,
        {} if cache is None else cache, ("fit", measurements), config["part_b"]["tuning"],
    )
    return fitted_model, measurements, outcomes


class HistoryTests(unittest.TestCase):
    def test_all_histories_share_inventory_dates_and_exact_windows(self):
        config = configuration()
        config["design"]["targets"] = ["Food", "Banks"]
        data = dataset(rows=24)
        frame, tuning, timing = history.run_stage({"value": data, "equal": data}, config)
        self.assertEqual(len(history.policies(config)), 18)
        self.assertEqual(set(frame["history"]), {"8", "12", "16", "expanding"})
        self.assertEqual(timing["pca_fits"], 8)  # two M, inner/outer, two weightings; never multiplied by L or target.
        groups = frame.groupby(["weighting", "target", "history", "policy_id"])
        for _, group in groups:
            self.assertEqual(group["origin_index"].tolist(), [20, 21, 22, 23])
        for row in tuning:
            length = None if row["history"] == "expanding" else int(row["history"])
            self.assertEqual(row["inner_coef_stop"], 16)
            self.assertEqual(row["outer_coef_stop"], 20)
            self.assertEqual(row["inner_coef_start"], 0 if length is None else 16 - length)
            self.assertEqual(row["outer_coef_start"], 0 if length is None else 20 - length)
            if row["method"] in history.FACTOR_METHODS:
                self.assertEqual(row["inner_pca_stop"], 16)
                self.assertEqual(row["outer_pca_stop"], 20)
            if row["measurement_panel"] == "S":
                self.assertEqual(row["measurement_assets"], list(pilot.S))
            if row["outcome_panel"] == "target":
                self.assertEqual(row["outcome_assets"], [row["target"]])
        persistence = frame.loc[frame["method"] == "persistence"]
        self.assertTrue(persistence["persistence_duplicate_across_histories"].all())
        self.assertTrue((persistence.groupby(["weighting", "target", "origin_index"])["prediction"].nunique() == 1).all())

    def test_no_supervised_method_uses_outcomes_older_than_finite_window(self):
        data = dataset(rows=24)
        y = data.Y.copy()
        y[:8] += np.arange(8)[:, None] * 1000
        changed = replace(data, Y=y)
        test_rows = np.arange(20, 24)
        for policy in history.policies(configuration()):
            with self.subTest(policy=policy["policy_id"]):
                original, measurements, outcomes = fitted(policy, data, start=8)
                perturbed, _, _ = fitted(policy, changed, start=8)
                left = history._predict(policy, original, data, "Food", measurements, outcomes, test_rows)
                right = history._predict(policy, perturbed, data, "Food", measurements, outcomes, test_rows)
                np.testing.assert_array_equal(left, right)
                if policy["method"] in history.FACTOR_METHODS:
                    np.testing.assert_array_equal(original.representation_.pca_.components_, perturbed.representation_.pca_.components_)

    def test_inner_pipeline_never_fits_validation_or_later_X_or_Y(self):
        data = dataset(rows=24)
        x, y, controls = data.X.copy(), data.Y.copy(), data.local_all.copy()
        x[16:] += 1000
        y[16:] -= 1000
        controls[16:] *= 100
        changed = replace(data, X=x, Y=y, local_all=controls)
        for policy in history.policies(configuration()):
            with self.subTest(policy=policy["policy_id"]):
                original, measurements, outcomes = fitted(policy, data, start=8, stop=16, pca_stop=16)
                perturbed, _, _ = fitted(policy, changed, start=8, stop=16, pca_stop=16)
                rows = np.arange(16, 20)
                np.testing.assert_array_equal(
                    history._predict(policy, original, data, "Food", measurements, outcomes, rows),
                    history._predict(policy, perturbed, data, "Food", measurements, outcomes, rows),
                )

    def test_only_expanding_PCA_can_use_old_predictor_rows(self):
        data = dataset(rows=24)
        x = data.X.copy()
        x[:8, 0] += np.arange(8) * 100
        changed = replace(data, X=x)
        declared = history.policies(configuration())
        factor = next(p for p in declared if p["policy_id"] == "factor_separate__M-all__O-target")
        left, _, _ = fitted(factor, data, start=8)
        right, _, _ = fitted(factor, changed, start=8)
        self.assertEqual(left.representation_.n_samples_seen_, 20)
        self.assertFalse(np.allclose(left.representation_.feature_scaler_.mean_, right.representation_.feature_scaler_.mean_))
        for method in ("ridge", "elasticnet", "pls", "local_history"):
            policy = next(p for p in declared if p["method"] == method and p["measurement_panel"] in {"all", "none"})
            original, measurements, outcomes = fitted(policy, data, start=8)
            perturbed, _, _ = fitted(policy, changed, start=8)
            rows = np.arange(20, 24)
            np.testing.assert_array_equal(
                history._predict(policy, original, data, "Food", measurements, outcomes, rows),
                history._predict(policy, perturbed, data, "Food", measurements, outcomes, rows),
            )

    def test_own_history_and_direct_scalers_use_exactly_the_same_L(self):
        data = dataset(rows=24)
        ti = NAMES.index("Food")
        declared = history.policies(configuration())
        policy = next(p for p in declared if p["method"] == "local_history")
        actual, _, _ = fitted(policy, data, start=8)
        expected = LinearRegression().fit(data.local_all[8:20, ti, :], data.Y[8:20, ti])
        np.testing.assert_array_equal(actual.coef_, expected.coef_)
        for method in ("ridge", "elasticnet", "pls"):
            policy = next(p for p in declared if p["method"] == method and p["measurement_panel"] == "all")
            model, _, _ = fitted(policy, data, start=8)
            fitted_direct = model[0]
            if method == "pls":
                # PLS's supervised fit receives exactly the 12 coefficient rows.
                self.assertEqual(len(fitted_direct.regressor_.x_scores_), 12)
            else:
                self.assertEqual(int(fitted_direct.feature_scaler_.n_samples_seen_), 12)
            design = np.column_stack([np.ones(12), data.local_all[8:20, ti, :]])
            np.testing.assert_allclose(model[1], np.linalg.lstsq(design, data.X[8:20], rcond=None)[0])
            np.testing.assert_allclose(model[2], np.linalg.lstsq(design, data.Y[8:20, ti], rcond=None)[0])

    def test_boundary_replay_and_expanding_control_match_original_pilot(self):
        data, config = dataset(), configuration()
        development, _, _ = history.run_stage({"value": data}, config, "development")
        final, _, _ = history.run_stage({"value": data}, config, "final")
        self.assertTrue((pd.to_datetime(development["response_date"]) <= pd.Timestamp("2021-08-13")).all())
        self.assertTrue((pd.to_datetime(final["response_date"]) >= pd.Timestamp("2021-08-14")).all())
        self.assertEqual(final["origin_index"].min(), 32)
        self.assertEqual(set(final.loc[final["origin_index"] == 32, "refit_index"]), {30})
        all_config = deepcopy(config)
        all_config["part_b"]["calendar"]["development_response_end"] = "2020-01-01"
        all_config["part_b"]["calendar"]["new_final_response_start"] = "2020-01-02"
        all_rows, _, _ = history.run_stage({"value": data}, all_config, "final")
        replay = all_rows.loc[all_rows["origin_index"].isin(final["origin_index"])].reset_index(drop=True)
        np.testing.assert_allclose(final["prediction"], replay["prediction"], rtol=1e-12, atol=1e-12)
        old_config = dict(
            design=config["design"], calendar=dict(final_response_start="2020-01-02"),
            experiment=dict(initial_train=20, validation_size=4, refit_every=5, factor_count=2,
                            **config["part_b"]["tuning"]),
        )
        old, _, _ = pilot.run_stage({"value": data}, old_config, "final")
        expanding = all_rows.loc[all_rows["history"] == "expanding"].reset_index(drop=True)
        self.assertEqual(old["policy_id"].tolist(), expanding["policy_id"].tolist())
        np.testing.assert_allclose(old["prediction"], expanding["prediction"], rtol=1e-12, atol=1e-12)

    def test_PCA_is_fitted_once_for_all_histories_and_outcome_rules(self):
        data, config = dataset(rows=24), configuration()
        captures = []
        original_fit = PCARepresentation.fit

        def capture(representation, x):
            captures.append(np.array(x, copy=True))
            return original_fit(representation, x)

        with patch.object(PCARepresentation, "fit", capture):
            history.run_stage({"value": data}, config)
        self.assertEqual(len(captures), 4)
        self.assertEqual(sorted(frame.shape for frame in captures), [(16, 6), (16, 8), (20, 6), (20, 8)])
        for frame in captures:
            columns = list(range(len(NAMES))) if frame.shape[1] == len(NAMES) else [NAMES.index(name) for name in pilot.S]
            np.testing.assert_array_equal(frame, data.X[:len(frame), columns])

    def test_invalid_first_cutoff_and_calendar_are_rejected(self):
        config = configuration()
        config["part_b"]["calendar"]["first_outer_cutoff_pairs"] = 19
        with self.assertRaisesRegex(ValueError, "max finite history plus validation"):
            history.run_stage({"value": dataset()}, config)
        config = configuration()
        data = dataset()
        with self.assertRaisesRegex(ValueError, "seven calendar days"):
            history.run_stage({"value": replace(data, response_dates=data.response_dates + pd.Timedelta(days=1))}, config)


if __name__ == "__main__":
    unittest.main()
