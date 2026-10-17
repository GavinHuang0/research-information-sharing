"""Data-unit, calendar-alignment, missingness and causal-feature checks."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from factorcast.data import load_daily_returns
from factorcast.features import build_weekly_dataset, build_weekly_feature_panels, weekly_variance


def daily_panel(weeks: int = 40) -> pd.DataFrame:
    dates = pd.date_range("2020-01-06", periods=weeks * 5, freq="B")
    weekly_levels = (np.arange(weeks) + 1) * 0.001
    returns = np.repeat(weekly_levels, 5)
    return pd.DataFrame({"A": returns, "B": returns * 1.5}, index=dates)


class DailyDataTests(unittest.TestCase):
    def load_csv(self, contents: str, units: str = "decimal") -> pd.DataFrame:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "returns.csv"
            path.write_text(contents, encoding="utf-8")
            return load_daily_returns(path, units=units)

    def test_explicit_unit_conversion_and_provenance(self) -> None:
        loaded = self.load_csv("date,A,B\n2020-01-06,1,-2\n2020-01-07,,0.5\n", units="percent")
        np.testing.assert_allclose(loaded["A"].iloc[0], 0.01)
        np.testing.assert_allclose(loaded["B"], [-0.02, 0.005])
        self.assertTrue(np.isnan(loaded["A"].iloc[1]))
        self.assertEqual(loaded.attrs["daily_missing_by_asset"], {"A": 1, "B": 0})
        self.assertEqual(len(loaded.attrs["source_sha256"]), 64)
        json.dumps(loaded.attrs)

    def test_invalid_dates_units_values_and_headers_are_rejected(self) -> None:
        cases = [
            ("date,A\n2020-01-07,.01\n2020-01-06,.02\n", "decimal"),
            ("date,A\n2020-01-06,.01\n2020-01-06,.02\n", "decimal"),
            ("date,A\nnot-a-date,.01\n", "decimal"),
            ("date,A\n2020-01-06T13:00:00,.01\n", "decimal"),
            ("date,A\n2020-01-06,inf\n", "decimal"),
            ("date,A\n2020-01-06,invalid\n", "decimal"),
            ("date,A\n2020-01-06,-99.99\n", "percent"),
            ("date,A\n2020-01-06,-999\n", "decimal"),
            ("date,A,A\n2020-01-06,.01,.02\n", "decimal"),
            ("date,A\n2020-01-06,.01\n", "automatic"),
        ]
        for contents, units in cases:
            with self.subTest(contents=contents, units=units):
                with self.assertRaises(ValueError):
                    self.load_csv(contents, units=units)

    def test_compact_calendar_dates_do_not_become_nanosecond_timestamps(self) -> None:
        loaded = self.load_csv("date,A\n20200106,.01\n20200107,.02\n")
        self.assertEqual(loaded.index[0], pd.Timestamp("2020-01-06"))


class WeeklyFeatureTests(unittest.TestCase):
    def test_feature_panels_distinguish_volatility_variance_and_log_histories(self) -> None:
        returns = daily_panel(weeks=14)
        offset = 1e-8
        panels = build_weekly_feature_panels(returns, log_offset=offset)
        self.assertEqual(set(panels.as_dict()), {
            "variance", "volatility", "log_variance", "log_variance_mean_4w",
            "log_variance_mean_12w", "observed_daily_counts",
        })
        expected_variance = 5 * (np.arange(14) + 1) ** 2 * 0.001**2
        np.testing.assert_allclose(panels.variance["A"], expected_variance)
        np.testing.assert_allclose(panels.volatility["A"], np.sqrt(expected_variance))
        np.testing.assert_allclose(panels.volatility.pow(2), panels.variance)
        np.testing.assert_allclose(panels.log_variance["A"], np.log(expected_variance + offset))
        self.assertAlmostEqual(
            panels.log_variance_mean_4w["A"].iloc[3], np.log(expected_variance[:4] + offset).mean()
        )
        self.assertNotAlmostEqual(
            panels.log_variance_mean_4w["A"].iloc[3], np.log(expected_variance[:4].mean() + offset)
        )
        self.assertAlmostEqual(
            panels.log_variance_mean_12w["A"].iloc[11], np.log(expected_variance[:12] + offset).mean()
        )
        self.assertTrue(panels.log_variance_mean_4w.iloc[:3].isna().all().all())
        self.assertTrue(panels.log_variance_mean_12w.iloc[:11].isna().all().all())
        self.assertTrue((panels.observed_daily_counts == 5).all().all())
        for frame in panels.as_dict().values():
            self.assertTrue(frame.index.equals(panels.variance.index))
            self.assertEqual(list(frame.columns), ["A", "B"])

    def test_partial_endpoint_and_absent_weeks_keep_counts_and_calendar(self) -> None:
        returns = daily_panel(weeks=5).loc["2020-01-08":"2020-02-04"].copy()
        returns.loc[pd.Timestamp("2020-01-08"), "B"] = np.nan
        returns = returns.loc[~returns.index.isin(pd.date_range("2020-01-20", "2020-01-24"))]
        panels = build_weekly_feature_panels(returns)
        self.assertTrue(panels.variance.index.equals(pd.date_range("2020-01-10", periods=5, freq="W-FRI")))
        np.testing.assert_array_equal(panels.observed_daily_counts["A"], [3, 5, 0, 5, 2])
        np.testing.assert_array_equal(panels.observed_daily_counts["B"], [2, 5, 0, 5, 2])
        self.assertAlmostEqual(panels.variance["A"].iloc[0], 3 * 0.001**2)
        self.assertTrue(np.isnan(panels.variance["B"].iloc[0]))
        self.assertTrue(panels.variance.iloc[[2, 4]].isna().all().all())
        self.assertTrue(panels.volatility.iloc[[2, 4]].isna().all().all())
        self.assertTrue(panels.log_variance_mean_4w.isna().all().all())

    def test_variance_min_observations_and_no_fill(self) -> None:
        returns = daily_panel()
        returns.loc[returns.index[:3], "A"] = np.nan
        weekly = weekly_variance(returns, min_week_obs=3)
        self.assertTrue(np.isnan(weekly["A"].iloc[0]))
        self.assertAlmostEqual(weekly["B"].iloc[0], 5 * 0.0015**2)
        self.assertAlmostEqual(weekly["A"].iloc[1], 5 * 0.002**2)
        with self.assertRaises(ValueError):
            weekly_variance(returns, min_week_obs=0)

    def test_next_week_alignment_and_trailing_controls(self) -> None:
        returns = daily_panel()
        offset = 1e-8
        dataset = build_weekly_dataset(returns, target="B", log_offset=offset)
        logs = np.log(weekly_variance(returns) + offset)
        self.assertEqual(dataset.asset_names, ("A", "B"))
        self.assertEqual(dataset.target_index, 1)
        self.assertEqual(dataset.X.shape, (28, 2))
        self.assertEqual(dataset.Y.shape, (28, 2))
        self.assertEqual(dataset.local_all.shape, (28, 2, 3))
        self.assertTrue((dataset.response_dates - dataset.origin_dates == pd.Timedelta(days=7)).all())
        np.testing.assert_allclose(dataset.X[0], logs.iloc[11])
        np.testing.assert_allclose(dataset.Y[0], logs.iloc[12])
        np.testing.assert_allclose(dataset.local[0], [logs["B"].iloc[11], logs["B"].iloc[8:12].mean(), logs["B"].iloc[:12].mean()])
        np.testing.assert_allclose(dataset.y, dataset.Y[:, 1])
        json.dumps(dataset.report)

    def test_absent_calendar_week_never_becomes_a_two_week_response(self) -> None:
        returns = daily_panel(weeks=45)
        missing_week = pd.Timestamp("2020-05-22")
        week_labels = returns.index.to_period("W-FRI").end_time.normalize()
        returns = returns.loc[week_labels != missing_week]
        weekly = weekly_variance(returns)
        self.assertIn(missing_week, weekly.index)
        self.assertTrue(weekly.loc[missing_week].isna().all())
        dataset = build_weekly_dataset(returns, target="A")
        for origin in [missing_week - pd.Timedelta(days=7), missing_week, missing_week + pd.Timedelta(weeks=11)]:
            self.assertNotIn(origin, dataset.origin_dates)
        self.assertIn(missing_week + pd.Timedelta(weeks=12), dataset.origin_dates)
        self.assertTrue((dataset.response_dates - dataset.origin_dates == pd.Timedelta(days=7)).all())

    def test_future_return_changes_do_not_change_earlier_predictors(self) -> None:
        returns = daily_panel()
        cutoff = pd.Timestamp("2020-06-05")
        baseline = build_weekly_dataset(returns, target="A")
        changed = returns.copy()
        changed.loc[changed.index > cutoff] *= 7
        original_panels = build_weekly_feature_panels(returns)
        changed_panels = build_weekly_feature_panels(changed)
        for name, original in original_panels.as_dict().items():
            with self.subTest(panel=name):
                pd.testing.assert_frame_equal(
                    original.loc[:cutoff], changed_panels.as_dict()[name].loc[:cutoff]
                )
        perturbed = build_weekly_dataset(changed, target="A")
        mask = baseline.origin_dates <= cutoff
        self.assertTrue(baseline.origin_dates.equals(perturbed.origin_dates))
        np.testing.assert_array_equal(baseline.X[mask], perturbed.X[mask])
        np.testing.assert_array_equal(baseline.local_all[mask], perturbed.local_all[mask])
        earlier_responses = baseline.response_dates <= cutoff
        np.testing.assert_array_equal(baseline.Y[earlier_responses], perturbed.Y[earlier_responses])

    def test_no_valid_sample_and_invalid_offset_are_explicit_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, "No complete"):
            build_weekly_dataset(daily_panel(weeks=5), target="A")
        with self.assertRaises(ValueError):
            build_weekly_dataset(daily_panel(), target="missing")
        with self.assertRaises(ValueError):
            build_weekly_dataset(daily_panel(), target="A", log_offset=0)


if __name__ == "__main__":
    unittest.main()
