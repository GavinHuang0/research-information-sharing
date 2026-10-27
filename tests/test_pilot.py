"""Synthetic membership, phase-replay, and causality checks for the fixed pilot."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import unittest

import numpy as np
import pandas as pd

from factorcast.features import ForecastDataset
from factorcast.models import FactorForecaster
from factorcast.pilot import S, policies, prepare_panels, run_stage


NAMES = ("Other1", "Oil", "Hlth", "Banks", "Other2", "Food", "Mach", "Util")


def configuration() -> dict:
    return dict(
        design=dict(targets=["Food"], small_panel=list(S)),
        experiment=dict(initial_train=12, validation_size=4, refit_every=5, factor_count=2,
                        ridge_penalties=[0.01, 0.1], elasticnet_penalties=[0.001, 0.1],
                        pooling_penalties=[0.01, 1.0]),
        calendar=dict(origin_start="2020-01-01", response_end="2024-12-31",
                      final_response_start="2021-05-15"),
        data=dict(min_week_obs=3, log_offset=1e-8),
    )


def synthetic_dataset(rows=28) -> ForecastDataset:
    rng = np.random.default_rng(281)
    factors = rng.normal(size=(rows + 1, 2))
    x = factors @ rng.normal(size=(2, len(NAMES))) + rng.normal(scale=0.5, size=(rows + 1, len(NAMES)))
    local = np.stack([x[:-1], np.roll(x[:-1], 1, axis=0), np.roll(x[:-1], 2, axis=0)], axis=2)
    origins = pd.date_range("2021-01-01", periods=rows, freq="W-FRI")
    return ForecastDataset(
        X=x[:-1], Y=x[1:], local=local[:, NAMES.index("Food"), :], local_all=local,
        origin_dates=origins, response_dates=origins + pd.Timedelta(days=7),
        asset_names=NAMES, target_name="Food", report={},
    )


class PilotTests(unittest.TestCase):
    def test_policies_are_fixed_and_separate_donors_are_not_duplicated(self):
        declared = policies(configuration())
        self.assertEqual(len(declared), 18)
        self.assertEqual(len({item["policy_id"] for item in declared}), 18)
        separate = [item for item in declared if item["method"] == "factor_separate"]
        self.assertEqual(len(separate), 2)
        self.assertTrue(all(item["outcome_panel"] == "target" for item in separate))
        self.assertEqual({item["measurement_panel"] for item in separate}, {"S", "all"})
        self.assertTrue(all(item["n_factors"] == 2 for item in declared
                            if item["method"].startswith("factor_") or item["method"] == "pls"))

    def test_prepare_warms_before_calendar_and_intersects_weightings_by_name(self):
        rng = np.random.default_rng(77)
        dates = pd.date_range("2019-08-05", periods=70 * 5, freq="B")
        value = pd.DataFrame(rng.normal(0, 0.01, size=(len(dates), len(NAMES))), index=dates, columns=NAMES)
        equal = value.iloc[:, ::-1].copy()
        equal.loc["2020-03-16":"2020-03-20", "Other1"] = np.nan
        datasets, report = prepare_panels({"value": value, "equal": equal}, configuration())
        left, right = datasets["value"], datasets["equal"]
        self.assertEqual(left.asset_names, NAMES)
        self.assertEqual(right.asset_names, NAMES)
        self.assertTrue(left.origin_dates.equals(right.origin_dates))
        self.assertTrue(left.response_dates.equals(right.response_dates))
        self.assertEqual(left.origin_dates[0], pd.Timestamp("2020-01-03"))
        self.assertNotIn(pd.Timestamp("2020-03-13"), left.origin_dates)
        self.assertNotIn(pd.Timestamp("2020-03-20"), left.origin_dates)
        np.testing.assert_array_equal(left.X, right.X)
        self.assertEqual(report["canonical_asset_names"], list(NAMES))
        self.assertGreater(report["common_pairs_before_calendar"], report["common_pairs"])

    def test_membership_is_not_a_prefix_and_column_permutations_preserve_forecasts(self):
        dataset = synthetic_dataset(rows=16)
        config = configuration()
        config["design"]["targets"] = ["Food", "Banks"]
        config["calendar"]["final_response_start"] = "2020-01-01"
        baseline, tuning, timing = run_stage({"value": dataset}, config, stage="final")
        self.assertEqual(timing["pca_fits"], 4)  # 2 measurement sets x inner/outer; shared over policies.
        for item in tuning:
            if item["measurement_panel"] == "S":
                self.assertEqual(item["measurement_assets"], list(S))
            if item["outcome_panel"] == "target":
                self.assertEqual(item["outcome_assets"], [item["target"]])
            if item["outcome_panel"] == "S":
                self.assertEqual(item["outcome_assets"], list(S))
            self.assertEqual(len(item["candidate_scores"]), 2 if item["method"] in
                             {"ridge", "elasticnet", "factor_partial"} else 1)
        permutation = np.arange(len(NAMES))[::-1]
        permuted = replace(
            dataset, X=dataset.X[:, permutation], Y=dataset.Y[:, permutation],
            local_all=dataset.local_all[:, permutation, :],
            asset_names=tuple(NAMES[index] for index in permutation),
        )
        reordered, _, _ = run_stage({"value": permuted}, config, stage="final")
        keys = ["target", "policy_id", "origin_index"]
        baseline = baseline.sort_values(keys).reset_index(drop=True)
        reordered = reordered.sort_values(keys).reset_index(drop=True)
        self.assertEqual(baseline[keys].to_dict("records"), reordered[keys].to_dict("records"))
        np.testing.assert_allclose(baseline["prediction"], reordered["prediction"], rtol=1e-8, atol=1e-8)
        # Banks is neither the first source industry nor the first S member.
        measurement_indices = [NAMES.index(name) for name in S]
        expected = FactorForecaster(n_factors=2, pooling="pooled").fit(
            dataset.X[:12, measurement_indices], dataset.Y[:12],
            target=NAMES.index("Banks"), local=dataset.local_all[:12],
        ).predict(dataset.X[12:, measurement_indices], local=dataset.local_all[12:])
        actual = baseline.loc[(baseline["target"] == "Banks") &
                              (baseline["policy_id"] == "factor_pooled__M-S__O-all"), "prediction"]
        np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-10)

    def test_phases_split_on_response_and_replay_the_original_refit_schedule(self):
        dataset = synthetic_dataset()
        config = configuration()
        development, _, _ = run_stage({"value": dataset}, config, stage="development")
        final, _, _ = run_stage({"value": dataset}, config, stage="final")
        boundary = pd.Timestamp(config["calendar"]["final_response_start"])
        self.assertTrue((pd.to_datetime(development["response_date"]) < boundary).all())
        self.assertTrue((pd.to_datetime(final["response_date"]) >= boundary).all())
        self.assertFalse(set(development["origin_index"]) & set(final["origin_index"]))
        first_final = int(final["origin_index"].min())
        anchored = 12 + ((first_final - 12) // 5) * 5
        self.assertNotEqual(first_final, anchored)
        self.assertEqual(set(final.loc[final["origin_index"] == first_final, "refit_index"]), {anchored})
        unsplit = deepcopy(config)
        unsplit["calendar"]["final_response_start"] = "2020-01-01"
        replay, _, _ = run_stage({"value": dataset}, unsplit, stage="final")
        replay = replay.loc[replay["origin_index"].isin(final["origin_index"])].reset_index(drop=True)
        np.testing.assert_allclose(final["prediction"], replay["prediction"], rtol=1e-13, atol=1e-13)
        self.assertEqual(set(development["origin_index"]) | set(final["origin_index"]), set(range(12, len(dataset.X))))

    def test_future_outcome_perturbation_cannot_change_first_block_fit_or_tuning(self):
        dataset = synthetic_dataset(rows=16)
        config = configuration()
        config["calendar"]["final_response_start"] = "2020-01-01"
        baseline, original_tuning, _ = run_stage({"value": dataset}, config, stage="final")
        changed_y = dataset.Y.copy()
        changed_y[12:] += 1000
        changed = replace(dataset, Y=changed_y)
        perturbed, new_tuning, _ = run_stage({"value": changed}, config, stage="final")
        np.testing.assert_array_equal(baseline["prediction"], perturbed["prediction"])
        self.assertEqual(original_tuning, new_tuning)
        self.assertFalse(np.array_equal(baseline["actual"], perturbed["actual"]))
        changed_x, changed_local = dataset.X.copy(), dataset.local_all.copy()
        changed_x[13:] += 1000
        changed_local[13:] -= 1000
        changed = replace(changed, X=changed_x, local_all=changed_local)
        future_predictors, future_tuning, _ = run_stage({"value": changed}, config, stage="final")
        first = baseline["origin_index"] == 12
        np.testing.assert_array_equal(baseline.loc[first, "prediction"], future_predictors.loc[first, "prediction"])
        self.assertEqual(original_tuning, future_tuning)


if __name__ == "__main__":
    unittest.main()
