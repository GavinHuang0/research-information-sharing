"""Checks for target-balanced aggregation and development-only selection."""

import unittest
from pathlib import Path
import importlib.util
import json
import tempfile

import numpy as np
import pandas as pd

from factorcast.pilot_reporting import choose_winners, summarize, write_reports


def prediction_fixture():
    rows = []
    # A difficult target has 100 times the baseline squared error.  Pooling
    # errors before taking ratios would reverse the apparent model ranking.
    for stage, start in (("development", "2020-01-03"), ("final", "2022-01-07")):
        for weighting in ("value", "equal"):
            for target, baseline in (("A", 1.0), ("B", 10.0)):
                for policy, method in (("local_history", "local_history"),
                                       ("factor_separate_s6", "factor_separate"),
                                       ("ridge_all", "ridge")):
                    error = baseline
                    if policy.startswith("factor"):
                        error = (0.5 if target == "A" else 12.0) if stage == "development" else 2 * baseline
                    if policy.startswith("ridge"):
                        error = 1.1 * baseline if stage == "development" else 0.1 * baseline
                    if weighting == "equal" and policy.startswith("ridge"):
                        error = 0.01 * baseline  # Must not influence selection.
                    for origin in pd.date_range(start, periods=3, freq="W-FRI"):
                        rows.append({
                            "weighting": weighting, "stage": stage, "target": target,
                            "policy_id": policy, "method": method,
                            "measurement_panel": "S6", "outcome_panel": "target",
                            "n_measurements": 6, "n_outcomes": 1, "n_factors": 2,
                            "origin_date": origin, "response_date": origin + pd.Timedelta(days=7),
                            "actual": 0.0, "prediction": error,
                            "squared_error": error ** 2, "absolute_error": abs(error),
                        })
    return pd.DataFrame(rows)


class PilotReportingTests(unittest.TestCase):
    def test_aggregate_uses_equal_target_ratios_not_pooled_mse_ratio(self):
        targets, aggregate = summarize(prediction_fixture())
        selected = aggregate[(aggregate.weighting == "value")
                             & (aggregate.stage == "development")
                             & (aggregate.policy_id == "factor_separate_s6")].iloc[0]
        self.assertAlmostEqual(selected.mean_ratio_mse, (0.25 + 1.44) / 2)
        self.assertAlmostEqual(selected.improvement_pct, 15.5)
        self.assertEqual(selected.n_targets, 2)
        self.assertEqual(selected.n_forecasts_per_target, 3)
        baseline_mse = targets[(targets.weighting == "value")
                               & (targets.stage == "development")
                               & (targets.policy_id == "local_history")].mse.mean()
        self.assertGreater(selected.mean_mse / baseline_mse, 1)

    def test_winners_ignore_final_and_equal_weighted_results(self):
        _, aggregate = summarize(prediction_fixture())
        self.assertEqual(choose_winners(aggregate), {
            "overall": "factor_separate_s6", "factor": "factor_separate_s6",
        })
        aggregate.loc[(aggregate.stage == "final") | (aggregate.weighting == "equal"), "mean_ratio_mse"] = 0
        self.assertEqual(choose_winners(aggregate)["overall"], "factor_separate_s6")

    def test_ties_resolve_by_policy_id(self):
        _, aggregate = summarize(prediction_fixture())
        aggregate.loc[(aggregate.stage == "development") & (aggregate.weighting == "value"), "mean_ratio_mse"] = 1
        self.assertEqual(choose_winners(aggregate)["overall"], "factor_separate_s6")

    def test_mismatched_date_sets_rejected(self):
        frame = prediction_fixture()
        with self.assertRaisesRegex(ValueError, "identical eligible dates"):
            summarize(frame.drop(index=0))

    def test_duplicate_forecasts_rejected(self):
        frame = prediction_fixture()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            summarize(pd.concat([frame, frame.iloc[[0]]], ignore_index=True))

    def test_stored_loss_must_match_actual_and_prediction(self):
        frame = prediction_fixture()
        frame.loc[0, "squared_error"] = 900
        with self.assertRaisesRegex(ValueError, "squared_error"):
            summarize(frame)
        targets, _ = summarize(prediction_fixture().drop(columns=["squared_error", "absolute_error"]))
        self.assertTrue(np.isfinite(targets.mse).all())

    def test_actual_outcomes_must_agree_across_policies(self):
        frame = prediction_fixture().drop(columns=["squared_error", "absolute_error"])
        frame.loc[0, "actual"] = 1
        with self.assertRaisesRegex(ValueError, "realized outcome"):
            summarize(frame)

    def test_zero_baseline_and_missing_policy_rejected(self):
        frame = prediction_fixture().drop(columns=["squared_error", "absolute_error"])
        frame.loc[frame.method == "local_history", "prediction"] = 0
        with self.assertRaisesRegex(ValueError, "positive"):
            summarize(frame)
        frame = prediction_fixture()
        frame = frame[~((frame.target == "A") & (frame.policy_id == "ridge_all"))]
        with self.assertRaisesRegex(ValueError, "missing a policy"):
            summarize(frame)

    def test_report_rejects_selection_using_final_sample(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            with self.assertRaisesRegex(ValueError, "frozen value-weighted development"):
                write_reports(prediction_fixture(), Path(temporary), {
                    "overall": "ridge_all", "factor": "factor_separate_s6",
                })
            self.assertEqual(list(Path(temporary).iterdir()), [])

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "plotting dependency is optional")
    def test_reports_include_all_policies_stages_weightings_and_frozen_choices(self):
        frame = prediction_fixture()
        _, aggregate = summarize(frame)
        winners = choose_winners(aggregate)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            output = Path(temporary)
            write_reports(frame, output, winners)
            saved = pd.read_csv(output / "aggregate_summary.csv")
            self.assertEqual(len(saved), 12)
            self.assertEqual(set(saved.stage), {"development", "final"})
            self.assertEqual(set(saved.weighting), {"value", "equal"})
            selection = json.loads((output / "selected_policies.json").read_text())
            self.assertEqual(selection["overall"], "factor_separate_s6")
            for name in ("aggregate_relative_improvement", "final_target_improvement",
                         "factor_mechanisms", "final_cumulative_paired_loss"):
                for extension in ("png", "pdf"):
                    self.assertGreater((output / f"{name}.{extension}").stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
