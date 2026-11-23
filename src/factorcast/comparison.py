"""Matched full-panel and two-component regressions for Experiment 4."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler

from .models import PCARepresentation
from .surface import FactorWindow, LocalWindow


def _ridge_path(train, outcome, score, penalties):
    """Predict on a fixed design for normalized MSE plus L2 penalty.

    The design and outcome have already been centered or residualized. The
    zero-penalty fit uses the same rank cutoff as default numpy least squares.
    """
    if train.shape[1] == 0:
        return {penalty: np.zeros(len(score)) for penalty in penalties}, 0, None
    left, singular, right = np.linalg.svd(train, full_matrices=False)
    retained = singular > np.finfo(float).eps * max(train.shape) * singular[0]
    rank = int(retained.sum())
    condition = float(singular[0] / singular[-1]) if rank == train.shape[1] else None
    fitted_coordinates = left.T @ outcome
    score_coordinates = score @ right.T
    predictions = {}
    for penalty in penalties:
        if penalty == 0:
            weights = np.divide(1.0, singular, out=np.zeros_like(singular), where=retained)
        else:
            weights = singular / (singular**2 + len(train) * penalty)
        predictions[penalty] = score_coordinates @ (weights * fitted_coordinates)
    return predictions, rank, condition


def predict_window(dataset, start, stop, rows, targets, penalties):
    """Fit each declared candidate on [start, stop) and forecast later rows.

    The primary panel and PC models use one set of training column scales.
    Native PC scores preserve the L2 penalty in the retained orthonormal
    subspace. All panel and PC fits account for unpenalized own-history controls.
    """
    rows = np.asarray(rows, dtype=int)
    targets = list(targets)
    if not 0 <= start < stop <= len(dataset.X) or len(rows) == 0 or np.any(rows < stop):
        raise ValueError("Forecast rows must follow a nonempty training window")
    training = slice(start, stop)
    ridge = penalties["ridge"]
    elasticnet = penalties["elasticnet"]
    grids = {
        "own_ols": (0.0,), "own_ridge": ridge, "own_elasticnet": elasticnet,
        "panel_ols": (0.0,), "panel_ridge": ridge, "pc_ols": (0.0,),
        "pc_ridge": ridge, "pc_common": (0.0,), "own_ridge_plus_pcs": ridge,
        "panel_ridge_legacy": ridge,
    }
    predictions = {
        method: {penalty: np.empty((len(rows), len(targets))) for penalty in grid}
        for method, grid in grids.items()
    }
    diagnostics = {"panel_residual_rank": [], "panel_condition_number": [], "panel_residual_df": []}

    raw_panel = dataset.X[training]
    pca = PCARepresentation(2).fit(raw_panel)
    standardized = pca.feature_scaler_.transform(raw_panel)
    standardized_score = pca.feature_scaler_.transform(dataset.X[rows])
    pc_train = pca.pca_.transform(standardized)
    pc_score = pca.pca_.transform(standardized_score)
    local_score = dataset.local_all[rows]
    outcome = dataset.Y[training]
    local = LocalWindow(outcome, dataset.local_all[training])
    factor = FactorWindow(local, pc_train)
    own_ols = local.predict(local_score, targets)
    predictions["own_ols"][0.0] = own_ols
    predictions["pc_common"][0.0] = factor.common(2).predict_scores(pc_score, local_score, targets)

    for position, target in enumerate(targets):
        own_prediction = own_ols[:, position]
        local_train = dataset.local_all[training, target]
        z_scaler = StandardScaler().fit(local_train)
        z_train = z_scaler.transform(local_train)
        z_score = z_scaler.transform(local_score[:, target])
        target_outcome = outcome[:, target]
        target_mean = target_outcome.mean()
        own_fits, _, _ = _ridge_path(z_train, target_outcome - target_mean, z_score, ridge)

        design = local.designs[:, target]
        design_score = np.column_stack([np.ones(len(rows)), local_score[:, target]])
        residual_y = local.residual_y[:, target]
        projection = np.linalg.lstsq(design, standardized, rcond=None)[0]
        residual_panel = standardized - design @ projection
        panel_score = standardized_score - design_score @ projection
        # The target's current weekly observation is the first local control.
        other_industries = np.arange(standardized.shape[1]) != target
        panel_fits, rank, condition = _ridge_path(
            residual_panel[:, other_industries], residual_y, panel_score[:, other_industries], ridge,
        )
        diagnostics["panel_residual_rank"].append(rank)
        diagnostics["panel_condition_number"].append(condition)
        diagnostics["panel_residual_df"].append(len(design) - int(np.linalg.matrix_rank(design)) - rank)

        residual_pcs = factor.residual_z[target]
        residual_pc_score = pc_score - design_score @ factor.z_projection[target]
        pc_fits, _, _ = _ridge_path(residual_pcs, residual_y, residual_pc_score, ridge)

        # Match the earlier direct ridge procedure's residual-column scaling.
        raw_residual_scale = residual_panel.std(axis=0) * pca.feature_scaler_.scale_
        legacy_columns = other_industries & (raw_residual_scale > 1e-10 * np.maximum(raw_panel.std(axis=0), 1.0))
        legacy_train = residual_panel[:, legacy_columns]
        legacy_score = panel_score[:, legacy_columns]
        if legacy_columns.any():
            legacy_scaler = StandardScaler().fit(legacy_train)
            legacy_train = legacy_scaler.transform(legacy_train)
            legacy_score = legacy_scaler.transform(legacy_score)
        residual_mean = residual_y.mean()
        legacy_fits, _, _ = _ridge_path(
            legacy_train, residual_y - residual_mean, legacy_score, ridge,
        )

        predictions["panel_ols"][0.0][:, position] = own_prediction + panel_fits[0.0]
        predictions["pc_ols"][0.0][:, position] = own_prediction + pc_fits[0.0]
        for penalty in ridge:
            own_ridge = own_prediction if penalty == 0 else target_mean + own_fits[penalty]
            predictions["own_ridge"][penalty][:, position] = own_ridge
            predictions["own_ridge_plus_pcs"][penalty][:, position] = own_ridge + pc_fits[0.0]
            predictions["panel_ridge"][penalty][:, position] = own_prediction + panel_fits[penalty]
            predictions["pc_ridge"][penalty][:, position] = own_prediction + pc_fits[penalty]
            predictions["panel_ridge_legacy"][penalty][:, position] = (
                own_prediction + residual_mean + legacy_fits[penalty]
            )
        for penalty in elasticnet:
            if penalty == 0:
                prediction = own_prediction
            else:
                fitted = ElasticNet(alpha=penalty, l1_ratio=penalties["elasticnet_l1_ratio"],
                                    tol=1e-10, max_iter=100000).fit(z_train, target_outcome)
                prediction = fitted.predict(z_score)
            predictions["own_elasticnet"][penalty][:, position] = prediction

    if not all(np.isfinite(values).all() for grid in predictions.values() for values in grid.values()):
        raise ValueError("A comparison produced nonfinite forecasts")
    return predictions, diagnostics
