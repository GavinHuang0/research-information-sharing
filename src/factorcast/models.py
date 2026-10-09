"""Forecasting baselines and shared-representation factor regression.

Every estimator consumes aligned pairs ``X_t -> Y_{t+1}`` and predicts a
single focal outcome. Preprocessing is learned exclusively in ``fit``. A
fitted :class:`PCARepresentation` can be passed to multiple factor models
to hold factor estimation fixed while changing outcome donors or pooling.
"""

from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import ArrayLike, NDArray
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler

FloatArray = NDArray[np.float64]


def _matrix(value: ArrayLike, name: str) -> FloatArray:
    result = np.asarray(value, dtype=float)
    if result.ndim != 2 or min(result.shape) < 1 or not np.isfinite(result).all():
        raise ValueError(f"{name} must be a finite, nonempty two-dimensional array")
    return result


def _training_arrays(
    X: ArrayLike, Y: ArrayLike, target: int
) -> tuple[FloatArray, FloatArray]:
    x = _matrix(X, "X")
    y = np.asarray(Y, dtype=float)
    if y.ndim == 1:
        y = y[:, None]
    y = _matrix(y, "Y")
    if x.shape[0] != y.shape[0] or x.shape[0] < 2:
        raise ValueError("X and Y must have the same number of rows, at least two")
    if not isinstance(target, (int, np.integer)) or not 0 <= target < y.shape[1]:
        raise ValueError("target must index a column of Y")
    return x, y


def _nonnegative(value: float, name: str) -> None:
    if value < 0 or not np.isfinite(value):
        raise ValueError(f"{name} must be finite and nonnegative")


class PanelForecaster(ABC):
    """Minimal estimator contract; predictions are a one-dimensional array."""

    @abstractmethod
    def fit(self, X: ArrayLike, Y: ArrayLike, target: int = 0):
        """Learn from training pairs and return self."""

    @abstractmethod
    def predict(self, X_new: ArrayLike) -> FloatArray:
        """Predict the focal outcome for each row."""


class PCARepresentation:
    """Training-column scaling, PCA, then training-score scaling.

    Standardizing scores gives partial-pooling and lasso penalties comparable
    across components. ``transform`` never changes fitted state. The rank
    cannot exceed min(number of columns, number of training rows minus one).
    """

    def __init__(self, n_factors: int = 2):
        if not isinstance(n_factors, (int, np.integer)) or n_factors < 1:
            raise ValueError("n_factors must be a positive integer")
        self.n_factors = n_factors

    def fit(self, X: ArrayLike):
        x = _matrix(X, "X")
        if self.n_factors > min(x.shape[1], x.shape[0] - 1):
            raise ValueError("n_factors exceeds the available centered matrix rank")
        self.n_features_in_ = x.shape[1]
        self.n_samples_seen_ = x.shape[0]
        self.feature_scaler_ = StandardScaler().fit(x)
        self.pca_ = PCA(n_components=self.n_factors, svd_solver="full")
        scores = self.pca_.fit_transform(self.feature_scaler_.transform(x))
        self.score_scaler_ = StandardScaler().fit(scores)
        return self

    def transform(self, X: ArrayLike) -> FloatArray:
        if not hasattr(self, "pca_"):
            raise RuntimeError("PCARepresentation must be fitted before transform")
        x = _matrix(X, "X")
        if x.shape[1] != self.n_features_in_:
            raise ValueError("X has a different number of predictor columns")
        scores = self.pca_.transform(self.feature_scaler_.transform(x))
        return self.score_scaler_.transform(scores)

    def fit_transform(self, X: ArrayLike) -> FloatArray:
        return self.fit(X).transform(X)


class FactorForecaster(PanelForecaster):
    """Regress all outcome columns on a shared, standardized PCA score matrix.

    ``pooling='separate'`` estimates an independent slope for each outcome.
    ``'pooled'`` estimates one common slope with outcome-specific intercepts.
    ``'partial'`` minimizes

    ``mean((Y - intercepts - Z @ slopes)**2)``
    ``+ penalty * mean_j(||slopes_j - mean_slope||**2)``.

    Thus ``penalty=0`` is separate regression and a large penalty approaches
    pooled regression, without a hidden dependence on donor count. A positive
    ``slope_penalty`` adds separate lasso fits for supervised selection among
    candidate PCs; it is supported only with separate pooling.

    Optional ``local`` arrays have shape T x outcome_count x local_count.
    Each asset has its own unpenalized local slopes and intercept; factor
    slopes are fitted jointly after partialling out those controls. Supply
    all donor controls again at prediction time.
    """

    def __init__(
        self,
        n_factors: int = 2,
        pooling: str = "separate",
        penalty: float = 0.0,
        representation: PCARepresentation | None = None,
        slope_penalty: float = 0.0,
    ):
        if pooling not in {"separate", "pooled", "partial"}:
            raise ValueError("pooling must be separate, pooled, or partial")
        _nonnegative(penalty, "penalty")
        _nonnegative(slope_penalty, "slope_penalty")
        if slope_penalty and pooling != "separate":
            raise ValueError("slope_penalty is supported only for separate regression")
        self.n_factors = n_factors
        self.pooling = pooling
        self.penalty = penalty
        self.representation = representation
        self.slope_penalty = slope_penalty

    def fit(
        self, X: ArrayLike, Y: ArrayLike, target: int = 0, local: ArrayLike | None = None
    ):
        x, y = _training_arrays(X, Y, target)
        self.target_ = target
        self.representation_ = self.representation or PCARepresentation(self.n_factors)
        if not hasattr(self.representation_, "pca_"):
            self.representation_.fit(x)
        z = self.representation_.transform(x)
        self.score_mean_ = z.mean(axis=0)
        self.outcome_mean_ = y.mean(axis=0)
        self.n_outcomes_ = y.shape[1]
        if local is None:
            local_values = np.empty((len(y), self.n_outcomes_, 0))
        else:
            local_values = self._local_array(local, len(y), self.n_outcomes_)
        self.n_local_features_ = local_values.shape[2]
        nuisance = [
            np.column_stack((np.ones(len(y)), local_values[:, j, :]))
            for j in range(self.n_outcomes_)
        ]
        residual_z = []
        residual_y = []
        for j, design in enumerate(nuisance):
            residual_z.append(z - design @ np.linalg.lstsq(design, z, rcond=None)[0])
            residual_y.append(
                y[:, j] - design @ np.linalg.lstsq(design, y[:, j], rcond=None)[0]
            )
        grams = np.stack([zj.T @ zj / len(y) for zj in residual_z])
        rhs = np.stack([
            zj.T @ yj / len(y) for zj, yj in zip(residual_z, residual_y)
        ])
        if self.slope_penalty:
            self.slopes_ = np.column_stack([
                Lasso(alpha=self.slope_penalty, fit_intercept=False, max_iter=20000)
                .fit(residual_z[j], residual_y[j]).coef_
                for j in range(self.n_outcomes_)
            ])
        elif self.pooling == "separate" or (
            self.pooling == "partial" and self.penalty == 0
        ):
            self.slopes_ = np.column_stack([
                np.linalg.lstsq(zj, yj, rcond=None)[0]
                for zj, yj in zip(residual_z, residual_y)
            ])
        else:
            common = np.linalg.lstsq(grams.sum(axis=0), rhs.sum(axis=0), rcond=None)[0]
            if self.pooling == "pooled":
                self.slopes_ = np.repeat(common[:, None], self.n_outcomes_, axis=1)
            elif self.n_local_features_ == 0:
                # With common residualized scores the mean slope is exactly
                # the pooled slope, giving a smaller, stable linear system.
                self.slopes_ = np.linalg.solve(
                    grams[0] + self.penalty * np.eye(z.shape[1]),
                    rhs.T + self.penalty * common[:, None],
                )
            else:
                # First-order conditions: G_j b_j + lambda(b_j - mean b)=h_j.
                k, m = z.shape[1], self.n_outcomes_
                system = np.kron(
                    np.eye(m) - np.ones((m, m)) / m, self.penalty * np.eye(k)
                )
                for j, gram in enumerate(grams):
                    system[j * k:(j + 1) * k, j * k:(j + 1) * k] += gram
                # Rank-deficient local/score designs admit minimum-norm slopes.
                self.slopes_ = np.linalg.lstsq(system, rhs.ravel(), rcond=None)[0].reshape(m, k).T
        self.nuisance_coefficients_ = np.stack([
            np.linalg.lstsq(design, y[:, j] - z @ self.slopes_[:, j], rcond=None)[0]
            for j, design in enumerate(nuisance)
        ])
        self.intercepts_ = self.nuisance_coefficients_[:, 0]
        self.local_slopes_ = self.nuisance_coefficients_[:, 1:]
        return self

    @staticmethod
    def _local_array(local: ArrayLike, rows: int, outcomes: int) -> FloatArray:
        values = np.asarray(local, dtype=float)
        if (
            values.ndim != 3 or values.shape[:2] != (rows, outcomes)
            or not np.isfinite(values).all()
        ):
            raise ValueError("local must be a finite T x outcome_count x local_count array")
        return values

    def predict_all(self, X_new: ArrayLike, local: ArrayLike | None = None) -> FloatArray:
        if not hasattr(self, "slopes_"):
            raise RuntimeError("FactorForecaster must be fitted before predict")
        z = self.representation_.transform(X_new)
        result = z @ self.slopes_ + self.intercepts_
        if local is None:
            if self.n_local_features_:
                raise ValueError("local controls are required because fit used them")
        else:
            values = self._local_array(local, len(z), self.n_outcomes_)
            if values.shape[2] != self.n_local_features_:
                raise ValueError("local has a different number of control columns")
            result = result + np.einsum("tjl,jl->tj", values, self.local_slopes_)
        return result

    def predict(self, X_new: ArrayLike, local: ArrayLike | None = None) -> FloatArray:
        return self.predict_all(X_new, local=local)[:, self.target_]


class DirectForecaster(PanelForecaster):
    """Direct ridge or elastic-net prediction using training-scaled predictors.

    ``penalty`` is the regularization weight on the normalized loss:
    ridge uses alpha = n_train * penalty; elastic net uses sklearn's alpha.
    Intercepts are unpenalized.
    """

    def __init__(self, method: str = "ridge", penalty: float = 1.0, l1_ratio: float = 0.5):
        if method not in {"ridge", "elasticnet"}:
            raise ValueError("method must be ridge or elasticnet")
        _nonnegative(penalty, "penalty")
        if not 0 <= l1_ratio <= 1:
            raise ValueError("l1_ratio must lie in [0, 1]")
        self.method = method
        self.penalty = penalty
        self.l1_ratio = l1_ratio

    def fit(self, X: ArrayLike, Y: ArrayLike, target: int = 0):
        x, y = _training_arrays(X, Y, target)
        self.feature_scaler_ = StandardScaler().fit(x)
        if self.penalty == 0:
            self.regressor_ = LinearRegression()
        elif self.method == "ridge":
            self.regressor_ = Ridge(alpha=len(x) * self.penalty)
        else:
            self.regressor_ = ElasticNet(
                alpha=self.penalty, l1_ratio=self.l1_ratio, max_iter=20000
            )
        self.regressor_.fit(self.feature_scaler_.transform(x), y[:, target])
        self.target_ = target
        return self

    def predict(self, X_new: ArrayLike) -> FloatArray:
        if not hasattr(self, "regressor_"):
            raise RuntimeError("DirectForecaster must be fitted before predict")
        return np.asarray(
            self.regressor_.predict(self.feature_scaler_.transform(_matrix(X_new, "X")))
        ).reshape(-1)


class PLSForecaster(PanelForecaster):
    """Target-supervised low-rank prediction with training-only scaling."""

    def __init__(self, n_components: int = 2):
        if not isinstance(n_components, (int, np.integer)) or n_components < 1:
            raise ValueError("n_components must be a positive integer")
        self.n_components = n_components

    def fit(self, X: ArrayLike, Y: ArrayLike, target: int = 0):
        x, y = _training_arrays(X, Y, target)
        if self.n_components > min(x.shape[1], x.shape[0] - 1):
            raise ValueError("n_components exceeds the available centered matrix rank")
        self.regressor_ = PLSRegression(n_components=self.n_components, scale=True)
        self.regressor_.fit(x, y[:, target])
        self.target_ = target
        return self

    def predict(self, X_new: ArrayLike) -> FloatArray:
        if not hasattr(self, "regressor_"):
            raise RuntimeError("PLSForecaster must be fitted before predict")
        return np.asarray(self.regressor_.predict(_matrix(X_new, "X"))).reshape(-1)


class OracleForecaster(PanelForecaster):
    """Infeasible diagnostic: regress the focal outcome on observed true factors."""

    def fit(self, X: ArrayLike, Y: ArrayLike, target: int = 0):
        x, y = _training_arrays(X, Y, target)
        self.regressor_ = LinearRegression().fit(x, y[:, target])
        self.target_ = target
        return self

    def predict(self, X_new: ArrayLike) -> FloatArray:
        if not hasattr(self, "regressor_"):
            raise RuntimeError("OracleForecaster must be fitted before predict")
        return np.asarray(self.regressor_.predict(_matrix(X_new, "X"))).reshape(-1)
