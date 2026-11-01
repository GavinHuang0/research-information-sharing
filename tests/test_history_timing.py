"""Independent Experiment 2 calendar and cross-boundary timing audits."""

from dataclasses import replace
from pathlib import Path
import tomllib
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from factorcast import history
from factorcast.data import load_daily_returns
from factorcast.features import ForecastDataset
from factorcast.pilot import S, prepare_panels


ROOT = Path(__file__).resolve().parents[1]


class HistoryTimingAuditTests(unittest.TestCase):
    def test_extended_committed_calendar_without_fitting_empirical_models(self):
        with (ROOT / "configs/experiment_02_plan.toml").open("rb") as handle:
            plan = tomllib.load(handle)
        calendar = plan["part_b"]["calendar"]
        preparation = dict(
            design=plan["design"], data=plan["data"],
            calendar=dict(
                origin_start=calendar["origin_start"],
                response_end=calendar["new_final_response_end"],
                final_response_start=calendar["new_final_response_start"],
            ),
        )
        returns = {
            weighting: load_daily_returns(
                ROOT / plan["data"][f"{weighting}_returns"], units="decimal"
            )
            for weighting in ("value", "equal")
        }
        datasets, _ = prepare_panels(returns, preparation)
        value, equal = datasets["value"], datasets["equal"]
        self.assertEqual(len(value.X), 1377)
        self.assertEqual(len(value.asset_names), 48)
        self.assertTrue(value.origin_dates.equals(equal.origin_dates))
        self.assertTrue(value.response_dates.equals(equal.response_dates))
        self.assertTrue(
            ((value.response_dates - value.origin_dates) == pd.Timedelta(days=7)).all()
        )
        self.assertEqual(value.response_dates[572], pd.Timestamp("2011-04-01"))
        self.assertEqual(value.response_dates[-1], pd.Timestamp("2026-08-28"))
        final_mask = value.response_dates >= pd.Timestamp("2025-01-03")
        self.assertEqual(int(final_mask.sum()), 87)
        self.assertEqual(int((~final_mask[572:]).sum()), 718)
        first_final = int(np.flatnonzero(final_mask)[0])
        self.assertEqual(first_final, 1290)
        anchor = 572 + ((first_final - 572) // 13) * 13
        self.assertEqual(anchor, 1287)
        self.assertEqual(value.origin_dates[anchor], pd.Timestamp("2024-12-06"))
        self.assertEqual(value.response_dates[anchor - 1], pd.Timestamp("2024-12-06"))
        self.assertEqual(value.response_dates[anchor], pd.Timestamp("2024-12-13"))
        self.assertEqual(value.origin_dates[first_final], pd.Timestamp("2024-12-27"))
        self.assertEqual(int(final_mask[anchor:anchor + 13].sum()), 10)
        self.assertEqual(value.origin_dates[anchor + 13], pd.Timestamp("2025-03-07"))
        self.assertEqual(value.response_dates[anchor - 53], pd.Timestamp("2023-12-08"))
        self.assertEqual(value.origin_dates[anchor - 52], pd.Timestamp("2023-12-08"))

    @staticmethod
    def synthetic_inputs():
        rng = np.random.default_rng(1327)
        names = ("Other", "Oil", "Banks", "Hlth", "Mach", "Food", "Util")
        rows = 28
        x = rng.normal(size=(rows, len(names)))
        local = np.stack(
            (x, rng.normal(size=x.shape), rng.normal(size=x.shape)), axis=2
        )
        y = 0.6 * x + rng.normal(scale=0.5, size=x.shape)
        origins = pd.date_range("2021-01-01", periods=rows, freq="W-FRI")
        data = ForecastDataset(
            X=x, Y=y, local=local[:, names.index("Food"), :], local_all=local,
            origin_dates=origins, response_dates=origins + pd.Timedelta(days=7),
            asset_names=names, target_name="Food", report={},
        )
        config = dict(
            design=dict(targets=["Food"], small_panel=list(S), factor_count=2),
            part_b=dict(
                calendar=dict(
                    first_outer_cutoff_pairs=18, refit_every_pairs=5,
                    development_response_end=data.response_dates[24].date().isoformat(),
                    new_final_response_start=data.response_dates[25].date().isoformat(),
                    new_final_response_end=data.response_dates[-1].date().isoformat(),
                ),
                history=dict(
                    finite_coefficient_pairs=[6, 10, 14],
                    include_expanding_control=True, validation_pairs=4,
                ),
                tuning=dict(
                    ridge_penalties=[0.01, 0.1], elasticnet_penalties=[0.001],
                    pooling_penalties=[0.1], elasticnet_l1_ratio=0.5,
                    elasticnet_tolerance=1e-10, elasticnet_max_iterations=100000,
                ),
            ),
        )
        return data, config

    def test_boundary_fit_ignores_later_development_and_final_outcomes(self):
        data, config = self.synthetic_inputs()
        declared = [
            p for p in history.policies(config)
            if p["policy_id"] in {
                "factor_pooled__M-all__O-all", "ridge__M-all__O-target",
                "pls__M-all__O-target", "local_history__M-none__O-target",
            }
        ]
        changed_y = data.Y.copy()
        # The scheduled fit is at 23. Outcomes 23/24 are development outcomes
        # observed before the first final forecast, but after that refit.
        changed_y[23:] += 1000.0
        with patch("factorcast.history.policies", return_value=declared):
            baseline, old_tuning, timing = history.run_stage(
                {"value": data, "equal": data}, config, "final"
            )
            changed, new_tuning, _ = history.run_stage(
                {"value": replace(data, Y=changed_y), "equal": replace(data, Y=changed_y)},
                config, "final",
            )
        self.assertEqual(set(baseline["origin_index"]), {25, 26, 27})
        self.assertEqual(set(baseline["refit_index"]), {23})
        self.assertEqual(set(baseline["history"]), {"6", "10", "14", "expanding"})
        self.assertEqual(timing["pca_fits"], 4)  # Inner/outer, two weightings; shared across L.
        np.testing.assert_array_equal(baseline["prediction"], changed["prediction"])
        self.assertEqual(old_tuning, new_tuning)
        for row in old_tuning:
            length = None if row["history"] == "expanding" else int(row["history"])
            self.assertEqual(row["inner_coef_stop"], 19)
            self.assertEqual(row["outer_coef_stop"], 23)
            self.assertEqual(row["inner_coef_start"], 0 if length is None else 19 - length)
            self.assertEqual(row["outer_coef_start"], 0 if length is None else 23 - length)
            if row["method"] == "factor_pooled":
                self.assertEqual(row["inner_pca_stop"], 19)
                self.assertEqual(row["outer_pca_stop"], 23)

    def test_pooled_recent_window_matches_independent_stacked_regression(self):
        data, config = self.synthetic_inputs()
        policy = next(
            p for p in history.policies(config)
            if p["policy_id"] == "factor_pooled__M-all__O-all"
        )
        names = data.asset_names
        model = history._fit_window(
            policy, 0.0, data, "Food", names, names, 9, 23, 23, {},
            ("independent_pooling_audit",), config["part_b"]["tuning"],
        )
        self.assertEqual(model.representation_.n_samples_seen_, 23)
        np.testing.assert_allclose(
            model.representation_.feature_scaler_.mean_, data.X[:23].mean(axis=0)
        )
        z = model.representation_.transform(data.X[9:23])
        residual_x, residual_y, nuisance = [], [], []
        for industry in range(len(names)):
            design = np.column_stack((np.ones(14), data.local_all[9:23, industry]))
            outcome = data.Y[9:23, industry]
            residual_x.append(z - design @ np.linalg.lstsq(design, z, rcond=None)[0])
            residual_y.append(outcome - design @ np.linalg.lstsq(design, outcome, rcond=None)[0])
            nuisance.append(design)
        slope = np.linalg.lstsq(np.vstack(residual_x), np.concatenate(residual_y), rcond=None)[0]
        expected = []
        future_scores = model.representation_.transform(data.X[23:])
        for industry, design in enumerate(nuisance):
            local_coefficients = np.linalg.lstsq(
                design, data.Y[9:23, industry] - z @ slope, rcond=None
            )[0]
            future_design = np.column_stack((np.ones(5), data.local_all[23:, industry]))
            expected.append(future_scores @ slope + future_design @ local_coefficients)
        np.testing.assert_allclose(
            model.predict_all(data.X[23:], local=data.local_all[23:]),
            np.column_stack(expected), rtol=1e-11, atol=1e-11,
        )


if __name__ == "__main__":
    unittest.main()
