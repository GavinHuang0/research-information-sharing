"""Tests for training-only transforms and distinct information-sharing limits."""

import unittest

import numpy as np
from sklearn.linear_model import LinearRegression

from factorcast.models import (
    DirectForecaster, FactorForecaster, OracleForecaster,
    PCARepresentation, PLSForecaster,
)


class ModelTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(42)
        self.X = rng.normal(size=(100, 6))
        self.Y = self.X[:, :2] @ np.array([[1, 1, 1], [0.3, 2, -1]])
        self.Y += rng.normal(scale=0.1, size=self.Y.shape)
        self.new_X = rng.normal(size=(12, 6))

    def test_transform_does_not_learn_from_test_rows(self):
        representation = PCARepresentation(3).fit(self.X)
        feature_mean = representation.feature_scaler_.mean_.copy()
        feature_scale = representation.feature_scaler_.scale_.copy()
        score_mean = representation.score_scaler_.mean_.copy()
        components = representation.pca_.components_.copy()
        prediction = representation.transform(self.new_X[:1])
        representation.transform(np.concatenate((self.new_X, self.new_X * 1e6)))
        np.testing.assert_allclose(representation.transform(self.new_X[:1]), prediction)
        np.testing.assert_array_equal(representation.feature_scaler_.mean_, feature_mean)
        np.testing.assert_array_equal(representation.feature_scaler_.scale_, feature_scale)
        np.testing.assert_array_equal(representation.score_scaler_.mean_, score_mean)
        np.testing.assert_array_equal(representation.pca_.components_, components)
        scores = representation.transform(self.X)
        np.testing.assert_allclose(scores.mean(axis=0), 0, atol=1e-14)
        np.testing.assert_allclose(scores.std(axis=0), 1)

    def test_partial_pooling_limits_and_shared_representation(self):
        representation = PCARepresentation(4).fit(self.X)
        original_components = representation.pca_.components_.copy()
        fitted = {
            name: FactorForecaster(
                representation=representation, pooling=pooling, penalty=penalty
            ).fit(self.X, self.Y)
            for name, pooling, penalty in (
                ("separate", "separate", 0), ("zero", "partial", 0),
                ("pooled", "pooled", 0), ("large", "partial", 1e8),
            )
        }
        np.testing.assert_allclose(fitted["zero"].predict(self.new_X), fitted["separate"].predict(self.new_X))
        np.testing.assert_allclose(fitted["large"].predict(self.new_X), fitted["pooled"].predict(self.new_X), atol=1e-7)
        self.assertGreater(np.linalg.norm(fitted["separate"].slopes_[:, 0] - fitted["pooled"].slopes_[:, 0]), 0.05)
        for model in fitted.values():
            self.assertIs(model.representation_, representation)
        np.testing.assert_array_equal(representation.pca_.components_, original_components)

    def test_separate_slopes_do_not_change_when_outcome_donors_are_added(self):
        representation = PCARepresentation(3).fit(self.X)
        single = FactorForecaster(representation=representation).fit(self.X, self.Y[:, :1])
        donors = FactorForecaster(representation=representation).fit(self.X, self.Y)
        np.testing.assert_allclose(single.predict(self.new_X), donors.predict(self.new_X))

    def test_local_controls_equal_full_ols_and_preserve_pooling_limits(self):
        rng = np.random.default_rng(91)
        local = rng.normal(size=(100, 3, 2))
        new_local = rng.normal(size=(12, 3, 2))
        Y = self.Y + 3 * local[:, :, 0] - local[:, :, 1]
        representation = PCARepresentation(3).fit(self.X)
        separate = FactorForecaster(representation=representation).fit(self.X, Y, local=local)
        full_ols = LinearRegression().fit(
            np.column_stack((representation.transform(self.X), local[:, 0, :])), Y[:, 0]
        )
        expected = full_ols.predict(
            np.column_stack((representation.transform(self.new_X), new_local[:, 0, :]))
        )
        np.testing.assert_allclose(separate.predict(self.new_X, local=new_local), expected, atol=1e-12)
        pooled = FactorForecaster(pooling="pooled", representation=representation).fit(self.X, Y, local=local)
        partial = FactorForecaster(pooling="partial", penalty=1e7, representation=representation).fit(self.X, Y, local=local)
        zero = FactorForecaster(pooling="partial", penalty=0, representation=representation).fit(self.X, Y, local=local)
        np.testing.assert_allclose(zero.predict(self.new_X, local=new_local), expected, atol=1e-12)
        np.testing.assert_allclose(partial.predict(self.new_X, local=new_local), pooled.predict(self.new_X, local=new_local), atol=1e-5)
        with self.assertRaises(ValueError):
            separate.predict(self.new_X)
        with self.assertRaises(ValueError):
            separate.predict(self.new_X, local=new_local[:, :1])

    def test_pooled_controls_match_stacked_constrained_regression(self):
        rng = np.random.default_rng(23)
        local = rng.normal(size=(100, 3, 1))
        Y = self.Y + 2 * local[:, :, 0] + np.array([5, -3, 7])
        representation = PCARepresentation(2).fit(self.X)
        z = representation.transform(self.X)
        model = FactorForecaster(pooling="pooled", representation=representation).fit(self.X, Y, local=local)
        # One joint OLS design encodes a shared factor slope and asset-specific
        # intercepts/local slopes, independently checking the FWL construction.
        design = np.zeros((300, 8))
        for j in range(3):
            rows = slice(j * 100, (j + 1) * 100)
            design[rows, :2] = z
            design[rows, 2 + j * 2] = 1
            design[rows, 3 + j * 2] = local[:, j, 0]
        coefficients = np.linalg.lstsq(design, Y.T.ravel(), rcond=None)[0]
        np.testing.assert_allclose(model.slopes_[:, 0], coefficients[:2], atol=1e-12)
        np.testing.assert_allclose(model.intercepts_, coefficients[2::2], atol=1e-12)
        np.testing.assert_allclose(model.local_slopes_[:, 0], coefficients[3::2], atol=1e-12)

    def test_candidate_factor_lasso_can_select_no_factors(self):
        model = FactorForecaster(n_factors=5, slope_penalty=100).fit(self.X, self.Y)
        np.testing.assert_array_equal(model.slopes_, np.zeros((5, 3)))
        np.testing.assert_allclose(model.predict(self.new_X), self.Y[:, 0].mean())

    def test_baselines_return_target_predictions(self):
        for model in (
            DirectForecaster("ridge", 0.1), DirectForecaster("elasticnet", 0.1),
            PLSForecaster(2), OracleForecaster(),
        ):
            with self.subTest(model=type(model).__name__):
                model.fit(self.X, self.Y, target=1)
                prediction = model.predict(self.new_X)
                self.assertEqual(prediction.shape, (12,))
                self.assertTrue(np.isfinite(prediction).all())

    def test_invalid_inputs_fail_before_fitting(self):
        with self.assertRaises(ValueError):
            FactorForecaster().fit(self.X, self.Y, target=3)
        with self.assertRaises(ValueError):
            PCARepresentation(7).fit(self.X)
        with self.assertRaises(ValueError):
            FactorForecaster(pooling="pooled", slope_penalty=1)
        with self.assertRaises(ValueError):
            DirectForecaster(penalty=-1)
        with self.assertRaises(ValueError):
            FactorForecaster().fit(self.X, self.Y, local=np.zeros((100, 1, 2)))


if __name__ == "__main__":
    unittest.main()
