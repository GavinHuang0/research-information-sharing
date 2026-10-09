import unittest

import numpy as np
from sklearn.linear_model import LinearRegression

from factorcast.experiments import _fit, _predict, evaluate_panel
from factorcast.simulation import SimulationConfig, generate_panel


class ExperimentTests(unittest.TestCase):
    def test_first_outer_forecasts_cannot_see_future_outcomes(self):
        panel = generate_panel(SimulationConfig(n_periods=70, max_assets=4, anchor_assets=2))
        settings = dict(measurement_assets=[2, 4], outcome_assets=[1, 4], factor_counts=[1, 2],
                        ridge_penalties=[0.1], lasso_penalties=[0.1], pooling_penalties=[1.0],
                        initial_train=45, validation_size=10, test_size=10, refit_every=5)
        original = evaluate_panel(panel.X, panel.Y, settings, {})[0]
        changed_y = panel.Y.copy()
        changed_y[45:] += 10000
        changed = evaluate_panel(panel.X, changed_y, settings, {})[0]
        first_a = [r["prediction"] for r in original if r["origin"] < 50]
        first_b = [r["prediction"] for r in changed if r["origin"] < 50]
        np.testing.assert_array_equal(first_a, first_b)
        # Adaptive policy emits exactly one forecast per outer date.
        adaptive = [r for r in original if r["method"] == "adaptive_factor"]
        self.assertEqual(len(adaptive), 10)
        self.assertEqual(len({r["origin"] for r in adaptive}), 10)

    def test_direct_baseline_retains_unpenalized_local_controls(self):
        rng = np.random.default_rng(4)
        X, local = rng.normal(size=(90, 4)), rng.normal(size=(90, 1, 3))
        Y = (X @ np.array([1., -.2, .3, .7]) + local[:, 0] @ np.array([5., -2., 1.]))[:, None]
        candidate = dict(method="direct_ridge", n_measurements=4, n_outcomes=1, k=0, penalty=0.)
        model = _fit(candidate, X, Y, local, slice(0, 60), {}, "test")
        expected = LinearRegression().fit(np.column_stack([local[:60, 0], X[:60]]), Y[:60, 0])
        np.testing.assert_allclose(_predict(candidate, model, X, local, slice(60, 90)),
                                   expected.predict(np.column_stack([local[60:, 0], X[60:]])), atol=1e-10)


if __name__ == "__main__":
    unittest.main()
