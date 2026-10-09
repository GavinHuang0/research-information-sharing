"""Tests for stationary, paired simulation construction."""

from dataclasses import replace
import unittest

import numpy as np

from factorcast.simulation import SimulationConfig, generate_panel


class SimulationTests(unittest.TestCase):
    def test_asset_prefix_is_invariant_to_larger_max_panel(self):
        config = SimulationConfig(n_periods=100, max_assets=8, anchor_assets=3, seed=17)
        small = generate_panel(config)
        large = generate_panel(replace(config, max_assets=13))
        repeat = generate_panel(config)
        for name in ("X", "Y", "conditional_mean"):
            np.testing.assert_allclose(getattr(small, name), getattr(large, name)[:, :8])
            np.testing.assert_array_equal(getattr(small, name), getattr(repeat, name))
        np.testing.assert_array_equal(small.factors, large.factors)
        np.testing.assert_array_equal(small.theta, large.theta[:8])

    def test_predictor_quality_and_coefficient_heterogeneity_are_independent(self):
        config = SimulationConfig(n_periods=80, max_assets=12, anchor_assets=3, seed=11)
        base = generate_panel(config)
        heterogeneous = generate_panel(replace(config, heterogeneity=3.0))
        irrelevant = generate_panel(replace(config, added_predictor_quality="irrelevant"))
        np.testing.assert_array_equal(base.X, heterogeneous.X)
        self.assertGreater(np.linalg.norm(base.theta - heterogeneous.theta), 0)
        np.testing.assert_array_equal(base.theta, irrelevant.theta)
        np.testing.assert_array_equal(base.Y, irrelevant.Y)
        np.testing.assert_array_equal(irrelevant.loadings[3:], 0)
        self.assertEqual(np.linalg.matrix_rank(base.loadings[:2]), 2)
        np.testing.assert_array_equal(base.theta[:, 0], np.ones(12))

    def test_forecast_pairs_have_declared_conditional_mean(self):
        panel = generate_panel(SimulationConfig(
            n_periods=70, max_assets=6, measurement_noise=0, outcome_noise=0
        ))
        np.testing.assert_allclose(panel.X, panel.factors @ panel.loadings.T)
        np.testing.assert_allclose(panel.Y, panel.factors @ panel.theta.T)
        np.testing.assert_array_equal(panel.Y, panel.conditional_mean)

    def test_optional_donor_shift_changes_donors_only(self):
        config = SimulationConfig(n_periods=60, max_assets=8, heterogeneity=0.7)
        centered = generate_panel(config)
        shifted = generate_panel(replace(config, donor_shift=1.5))
        np.testing.assert_array_equal(centered.X, shifted.X)
        np.testing.assert_array_equal(centered.Y[:, 0], shifted.Y[:, 0])
        np.testing.assert_allclose(shifted.theta[1:, 1] - centered.theta[1:, 1], 1.05)

    def test_invalid_configuration_is_rejected(self):
        for parameters in (
            {"factor_rho": 1}, {"measurement_correlation": -0.1},
            {"outcome_correlation": 1}, {"anchor_assets": 1},
            {"added_predictor_quality": "unknown"}, {"outcome_noise": -1},
        ):
            with self.subTest(parameters=parameters), self.assertRaises(ValueError):
                SimulationConfig(**parameters)


if __name__ == "__main__":
    unittest.main()
