"""Synthetic tables and render checks; no empirical forecasts or bootstrap."""

from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

import numpy as np
import pandas as pd

from factorcast.history_reporting import (
    FACTOR_POLICY, FIGURE_NAMES, REFERENCES, summarize_history, write_reports,
)
from factorcast.pilot import S, policies

HISTORIES = ("104", "260", "520", "expanding")


def prediction_fixture():
    rows = []
    declared = policies(dict(design=dict(targets=list(S), small_panel=list(S)), experiment=dict(factor_count=2)))
    for history_index, history in enumerate(HISTORIES):
        for stage, start in (("development", "2020-01-03"), ("final", "2025-01-03")):
            for weighting in ("value", "equal"):
                for target_index, target in enumerate(S):
                    base = (target_index + 1) * (1 + 0.05 * history_index)
                    for policy in declared:
                        ratio = 1.0 if policy["method"] == "local_history" else 0.98
                        if policy["policy_id"] == FACTOR_POLICY:
                            ratio = 0.95 - 0.03 * history_index + (0.1 if target == "Banks" else 0)
                        if policy["method"] == "ridge":
                            ratio = 0.9  # A direct method may win; reporter must not reselect it.
                        error = base * ratio
                        if policy["method"] == "persistence":
                            error = (target_index + 1) * 1.4  # Identical across history labels.
                        if weighting == "equal":
                            error *= 1.1
                        for origin in pd.date_range(start, periods=3, freq="W-FRI"):
                            rows.append(dict(
                                history=history, stage=stage, weighting=weighting, target=target, **policy,
                                n_measurements=0 if policy["measurement_panel"] == "none" else
                                6 if policy["measurement_panel"] == "S" else 48,
                                n_outcomes=1 if policy["outcome_panel"] == "target" else
                                6 if policy["outcome_panel"] == "S" else 48,
                                origin_date=origin, response_date=origin + pd.Timedelta(days=7),
                                actual=0.0, prediction=error, squared_error=error**2, absolute_error=abs(error),
                            ))
    return pd.DataFrame(rows)


def bootstrap_fixture(part):
    comparisons = []
    histories = ("expanding",) if part == "A" else HISTORIES
    for history in histories:
        for reference in REFERENCES:
            comparisons.append(("factor_vs_reference", history, reference, history))
    if part == "B":
        comparisons.extend(("history_vs_expanding", history, FACTOR_POLICY, "expanding") for history in HISTORIES[:-1])
    rows = []
    for weighting in ("value", "equal"):
        for block in (13, 6, 26):
            for index, (kind, history, reference, reference_history) in enumerate(comparisons):
                effect = 0.02 - 0.01 * (index % 4)
                low, high = effect - 0.03, effect + 0.04
                if part == "A" and index == 0:
                    low, high = -0.01, 0.01  # Valid basic CI need not contain the estimate.
                rows.append(dict(
                    part=part, stage="final", weighting=weighting, comparison_kind=kind,
                    comparison_id=f"{kind}_{history}_{reference}", candidate_policy=FACTOR_POLICY,
                    reference_policy=reference, candidate_history=history, reference_history=reference_history,
                    effect=effect, ci_low=low, ci_high=high, p_value=0.1 + index * 0.01,
                    p_adjusted=min(1.0, 0.4 + index * 0.01 + 0.001 * block),
                    block_length=block, is_primary_block=block == 13,
                    is_primary_weighting=weighting == "value", n_targets=6, n_dates=3,
                    index_sha256="synthetic_fixture_not_bootstrap_results",
                ))
    return pd.DataFrame(rows)


class HistoryReportingTests(unittest.TestCase):
    def test_summary_retains_every_cell_and_matches_history_baselines(self):
        targets, aggregate = summarize_history(prediction_fixture())
        self.assertEqual(len(targets), 1728)
        self.assertEqual(len(aggregate), 288)
        self.assertEqual(set(aggregate.history), set(HISTORIES))
        self.assertEqual(set(aggregate.stage), {"development", "final"})
        self.assertEqual(set(aggregate.weighting), {"value", "equal"})
        self.assertEqual(set(targets.target), set(S))
        for index, history in enumerate(HISTORIES):
            selected = aggregate.loc[(aggregate.history == history) & (aggregate.stage == "final")
                                     & (aggregate.weighting == "value") & (aggregate.policy_id == FACTOR_POLICY)].iloc[0]
            ratios = [(0.95 - 0.03 * index + (0.1 if target == "Banks" else 0))**2 for target in S]
            self.assertAlmostEqual(selected.mean_ratio_mse, np.mean(ratios))
        self.assertTrue(targets.loc[targets.method == "persistence", "persistence_duplicate_across_histories"].all())
        self.assertTrue((targets.loc[targets.method == "local_history", "ratio_mse"] == 1).all())

    def test_missing_history_policy_and_calendar_changes_are_rejected(self):
        frame = prediction_fixture()
        removed = frame.loc[~((frame.history == "104") & (frame.policy_id == REFERENCES[1]))]
        with self.assertRaisesRegex(ValueError, "same stages, weightings, targets, and policies"):
            summarize_history(removed)
        changed = frame.copy()
        mask = (changed.history == "104") & (changed.stage == "final")
        changed.loc[mask, "origin_date"] += pd.Timedelta(days=7)
        changed.loc[mask, "response_date"] += pd.Timedelta(days=7)
        with self.assertRaisesRegex(ValueError, "identical calendar pairs"):
            summarize_history(changed)

    def test_cross_history_actual_disagreement_is_rejected(self):
        frame = prediction_fixture().drop(columns=["squared_error", "absolute_error"])
        frame.loc[(frame.history == "104") & (frame.target == "Food"), "actual"] = 0.2
        with self.assertRaisesRegex(ValueError, "Histories disagree"):
            summarize_history(frame)

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib is optional")
    def test_reports_render_all_figures_and_keep_all_bootstrap_settings(self):
        frame = prediction_fixture()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            output = Path(temporary) / "reports"
            artifacts = write_reports(
                frame.loc[frame.stage == "development"], frame.loc[frame.stage == "final"],
                bootstrap_fixture("A"), bootstrap_fixture("B"), output,
            )
            self.assertEqual(len(pd.read_csv(output / artifacts["target_summary"])), 1728)
            self.assertEqual(len(pd.read_csv(output / artifacts["aggregate_summary"])), 288)
            saved_a, saved_b = pd.read_csv(output / artifacts["part_a_bootstrap"]), pd.read_csv(output / artifacts["part_b_bootstrap"])
            self.assertEqual(len(saved_a), 24)
            self.assertEqual(len(saved_b), 114)
            self.assertEqual(set(saved_b.block_length), {6, 13, 26})
            self.assertTrue((saved_a.effect < 0).any())
            manifest = json.loads((output / artifacts["manifest"]).read_text())
            self.assertEqual(manifest["factor_policy"], FACTOR_POLICY)
            self.assertTrue(manifest["no_new_winner_selection"])
            self.assertEqual(len(artifacts["figures"]), 12)
            for name in FIGURE_NAMES:
                for extension in ("png", "pdf"):
                    path = output / f"{name}.{extension}"
                    self.assertGreater(path.stat().st_size, 100)
            with self.assertRaises(FileExistsError):
                write_reports(frame.loc[frame.stage == "development"], frame.loc[frame.stage == "final"],
                              bootstrap_fixture("A"), bootstrap_fixture("B"), output)


if __name__ == "__main__":
    unittest.main()
