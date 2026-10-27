"""Independent fixed-snapshot calendar checks and synthetic boundary-fit audit."""

from dataclasses import replace
from pathlib import Path
import tomllib
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from factorcast.data import load_daily_returns
from factorcast.features import ForecastDataset
from factorcast.pilot import S, policies, prepare_panels, run_stage


ROOT = Path(__file__).resolve().parents[1]


class FixedPilotTimingTests(unittest.TestCase):
    def test_committed_sample_counts_and_boundary_anchor_without_forecasting(self):
        """Audit data alignment only; this test never fits an empirical model."""
        with (ROOT / "configs/fixed_pilot.toml").open("rb") as handle:
            config = tomllib.load(handle)
        returns = {
            weighting: load_daily_returns(
                ROOT / config["data"][f"{weighting}_returns"], units="decimal"
            )
            for weighting in ("value", "equal")
        }
        datasets, report = prepare_panels(returns, config)
        value, equal = datasets["value"], datasets["equal"]
        self.assertEqual(len(value.X), 1290)
        self.assertEqual(len(value.asset_names), 48)
        self.assertEqual(tuple(report["targets"]), S)
        self.assertTrue(value.origin_dates.equals(equal.origin_dates))
        self.assertTrue(value.response_dates.equals(equal.response_dates))
        self.assertTrue(
            ((value.response_dates - value.origin_dates) == pd.Timedelta(days=7)).all()
        )
        self.assertEqual(value.origin_dates[0], pd.Timestamp("2000-01-07"))
        self.assertEqual(value.response_dates[-1], pd.Timestamp("2024-12-27"))
        self.assertEqual(value.origin_dates[260], pd.Timestamp("2005-04-01"))
        self.assertEqual(value.response_dates[260], pd.Timestamp("2005-04-08"))
        expected_gap = pd.date_range("2001-09-07", "2001-11-30", freq="W-FRI")
        full_calendar = pd.date_range(
            value.origin_dates[0], value.origin_dates[-1], freq="W-FRI"
        )
        self.assertTrue(full_calendar.difference(value.origin_dates).equals(expected_gap))
        boundary = pd.Timestamp("2022-01-01")
        first_final = int(np.flatnonzero(value.response_dates >= boundary)[0])
        anchor = 260 + ((first_final - 260) // 13) * 13
        self.assertEqual(first_final, 1134)
        self.assertEqual(anchor, 1131)
        self.assertEqual(value.origin_dates[first_final], pd.Timestamp("2021-12-31"))
        self.assertEqual(value.response_dates[first_final], pd.Timestamp("2022-01-07"))
        self.assertEqual(value.origin_dates[anchor], pd.Timestamp("2021-12-10"))
        self.assertEqual(value.response_dates[anchor - 1], pd.Timestamp("2021-12-10"))
        self.assertEqual(int((value.response_dates[260:] < boundary).sum()), 874)
        self.assertEqual(int((value.response_dates >= boundary).sum()), 156)

    def test_boundary_replay_does_not_use_development_outcomes_after_its_refit(self):
        """Even realized pre-final outcomes must wait for the next fixed refit."""
        rng = np.random.default_rng(6091)
        rows = 28
        names = ("Other", *S)
        x = rng.normal(size=(rows, len(names)))
        y = 0.7 * x + rng.normal(scale=0.4, size=x.shape)
        local = np.stack(
            (x, rng.normal(size=x.shape), rng.normal(size=x.shape)), axis=2
        )
        origins = pd.date_range("2021-01-01", periods=rows, freq="W-FRI")
        dataset = ForecastDataset(
            X=x, Y=y, local=local[:, names.index("Food"), :], local_all=local,
            origin_dates=origins, response_dates=origins + pd.Timedelta(days=7),
            asset_names=names, target_name="Food", report={},
        )
        config = dict(
            design=dict(targets=["Food"], small_panel=list(S)),
            experiment=dict(
                initial_train=12, validation_size=4, refit_every=5, factor_count=2,
                ridge_penalties=[0.01, 0.1, 1.0],
                elasticnet_penalties=[0.001], pooling_penalties=[0.1],
            ),
            calendar=dict(final_response_start=dataset.response_dates[19].date().isoformat()),
        )
        declared = [
            item for item in policies(config)
            if item["method"] == "ridge" and item["measurement_panel"] == "S"
        ]
        # The boundary falls inside the block refitted at index 17. Change
        # both pre-final and final responses after that fit, before refit 22.
        changed_y = y.copy()
        changed_y[17:22] += 1000.0
        with patch("factorcast.pilot.policies", return_value=declared):
            original, old_tuning, _ = run_stage({"value": dataset}, config, "final")
            changed, new_tuning, _ = run_stage(
                {"value": replace(dataset, Y=changed_y)}, config, "final"
            )
        original_block = original.loc[original["refit_index"] == 17]
        changed_block = changed.loc[changed["refit_index"] == 17]
        self.assertEqual(original_block["origin_index"].to_list(), [19, 20, 21])
        np.testing.assert_array_equal(
            original_block["prediction"].to_numpy(), changed_block["prediction"].to_numpy()
        )
        old_boundary = [item for item in old_tuning if item["refit_index"] == 17]
        new_boundary = [item for item in new_tuning if item["refit_index"] == 17]
        self.assertEqual(old_boundary, new_boundary)
        self.assertEqual(old_boundary[0]["history_stop"], 17)
        self.assertEqual(
            old_boundary[0]["history_last_response"], dataset.response_dates[16].date().isoformat()
        )


if __name__ == "__main__":
    unittest.main()
