"""Authorization and immutable-plan gates without empirical execution."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("surface_orchestrator", ROOT / "scripts/run_experiment_03.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class Experiment3OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.config = tomllib.loads((ROOT / "configs/experiment_03.toml").read_text(encoding="utf-8"))

    def test_executable_config_preserves_plan_and_defers_calibration(self):
        RUNNER.validate_config(self.config)

    def test_scientific_changes_cannot_hide_in_executable_copy(self):
        changed = deepcopy(self.config)
        changed["partial_pooling"]["penalties"][0] = 0.02
        with self.assertRaises(ValueError):
            RUNNER.validate_config(changed)

    def test_storage_or_deferred_work_flags_are_guarded(self):
        for key, value in (("hard_file_bytes_must_be_less_than", 200_000_000), ("calibration_authorized", True), ("power_authorized", True)):
            changed = deepcopy(self.config)
            changed["execution"][key] = value
            with self.assertRaises(ValueError):
                RUNNER.validate_config(changed)

    def test_plan_cannot_be_redirected(self):
        changed = deepcopy(self.config)
        changed["execution"]["source_plan"] = "configs/experiment_03.toml"
        with self.assertRaises(ValueError):
            RUNNER.validate_config(changed)

    def test_stage_checksum_detects_modified_predictions(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "predictions.bin").write_bytes(b"original")
            RUNNER.finish_stage(directory)
            RUNNER.check_manifest(directory)
            (directory / "predictions.bin").write_bytes(b"modified")
            with self.assertRaises(ValueError):
                RUNNER.check_manifest(directory)

    def test_independent_audit_windows_handle_mode_column_and_all_roles(self):
        spec = importlib.util.spec_from_file_location("independent_surface_audit", ROOT / "scripts/audit_experiment_03.py")
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        cells = pd.DataFrame(dict(mode=["none", "matched", "expanding"], history=["104"] * 3,
                                  sharing=["own", "partial", "common"], K=[0, 2, 8]))
        chunk = pd.DataFrame(dict(cell_index=[0, 1, 2], refit_index=[572] * 3,
            coefficient_train_start=[468] * 3, coefficient_train_stop=[572] * 3,
            pca_train_start=[np.nan, 468, 0], pca_train_stop=[np.nan, 572, 572]))
        audit._windows(chunk, cells)
        changed = chunk.copy()
        changed.loc[1, "pca_train_start"] = 0
        with self.assertRaises(AssertionError):
            audit._windows(changed, cells)


if __name__ == "__main__":
    unittest.main()
