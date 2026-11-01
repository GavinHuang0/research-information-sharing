"""Experiment 2: recent supervised histories with shared expanding PCA.

The coefficient window includes every supervised operation, including direct
nuisance projections/scalers and PLS. Predictor-only PCA has its own expanding
cutoff and is reused across all histories and corresponding factor policies.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from .evaluation import mse
from .features import ForecastDataset
from .models import DirectForecaster, FactorForecaster, PCARepresentation, PLSForecaster
from .pilot import FACTOR_METHODS, PREDICTION_COLUMNS as PILOT_COLUMNS, S, policies as pilot_policies

PREDICTION_COLUMNS = PILOT_COLUMNS + [
    "history", "coefficient_train_start", "coefficient_train_stop",
    "pca_train_start", "pca_train_stop", "persistence_duplicate_across_histories",
]


def policies(config: dict) -> list[dict]:
    """Return the unchanged 18-policy inventory, before crossing with history."""
    return pilot_policies(dict(design=config.get("design", {}), experiment=dict(
        factor_count=config.get("design", {}).get("factor_count", 2))))


def _members(policy, target, names, small):
    measurements = (() if policy["measurement_panel"] == "none" else
                    small if policy["measurement_panel"] == "S" else names)
    outcomes = ((target,) if policy["outcome_panel"] == "target" else
                small if policy["outcome_panel"] == "S" else names)
    return tuple(measurements), tuple(outcomes)


def _penalties(policy, tuning):
    key = {"factor_partial": "pooling_penalties", "ridge": "ridge_penalties",
           "elasticnet": "elasticnet_penalties"}.get(policy["method"])
    values = [0.0] if key is None else tuning[key]
    if not values or any(not np.isfinite(value) or value < 0 for value in values):
        raise ValueError("Penalty grids must be finite, nonempty, and nonnegative")
    return [float(value) for value in values]


def _fit_window(policy, penalty, dataset, target, measurements, outcomes, start, stop,
                pca_stop, representations, cache_key, tuning):
    """Fit one pipeline; outcomes are accessed only within [start:stop)."""
    names = dataset.asset_names
    mi = [names.index(name) for name in measurements]
    oi = [names.index(name) for name in outcomes]
    ti = names.index(target)
    x, y = dataset.X[start:stop, mi], dataset.Y[start:stop, oi]
    local = dataset.local_all[start:stop, oi, :]
    method = policy["method"]
    if method == "persistence":
        return None
    if method == "local_history":
        return LinearRegression().fit(dataset.local_all[start:stop, ti, :], dataset.Y[start:stop, ti])
    if method in FACTOR_METHODS:
        if cache_key not in representations:
            representations[cache_key] = PCARepresentation(policy["n_factors"]).fit(dataset.X[:pca_stop, mi])
        return FactorForecaster(
            n_factors=policy["n_factors"], pooling=method.removeprefix("factor_"),
            penalty=penalty, representation=representations[cache_key],
        ).fit(x, y, target=outcomes.index(target), local=local)
    model = (PLSForecaster(policy["n_factors"]) if method == "pls" else DirectForecaster(
        method=method, penalty=penalty, l1_ratio=tuning.get("elasticnet_l1_ratio", 0.5)))
    design = np.column_stack([np.ones(stop - start), local[:, 0, :]])
    x_projection = np.linalg.lstsq(design, x, rcond=None)[0]
    y_projection = np.linalg.lstsq(design, y[:, 0], rcond=None)[0]
    residual_x = x - design @ x_projection
    mask = residual_x.std(axis=0) > 1e-10 * np.maximum(x.std(axis=0), 1.0)
    if method == "pls" and policy["n_factors"] > int(mask.sum()):
        raise ValueError("Fixed PLS dimension exceeds residual predictor rank")
    if mask.any():
        residual_y = y[:, 0] - design @ y_projection
        model.fit(residual_x[:, mask], residual_y)
        if method == "elasticnet" and penalty > 0:
            model.regressor_.set_params(
                tol=tuning.get("elasticnet_tolerance", 1e-10),
                max_iter=tuning.get("elasticnet_max_iterations", 100000),
            )
            model.regressor_.fit(model.feature_scaler_.transform(residual_x[:, mask]), residual_y)
    return model, x_projection, y_projection, mask


def _predict(policy, model, dataset, target, measurements, outcomes, rows):
    names = dataset.asset_names
    mi, oi = [names.index(name) for name in measurements], [names.index(name) for name in outcomes]
    x = dataset.X[rows][:, mi]
    local = dataset.local_all[rows][:, oi, :]
    ti, method = names.index(target), policy["method"]
    if method == "persistence":
        return dataset.local_all[rows, ti, 0]
    if method == "local_history":
        return model.predict(dataset.local_all[rows, ti, :])
    if method in FACTOR_METHODS:
        return model.predict(x, local=local)
    fitted, x_projection, y_projection, mask = model
    design = np.column_stack([np.ones(len(x)), local[:, 0, :]])
    result = design @ y_projection
    if mask.any():
        result = result + fitted.predict((x - design @ x_projection)[:, mask])
    return result


def _configuration(config):
    declared = policies(config)  # Also validates fixed two-component inventory and names.
    design = config.get("design", {})
    targets, small = tuple(design.get("targets", S)), tuple(design.get("small_panel", S))
    part = config["part_b"]
    calendar, settings = part["calendar"], part["history"]
    finite = settings["finite_coefficient_pairs"]
    integers = [calendar["first_outer_cutoff_pairs"], calendar["refit_every_pairs"],
                settings["validation_pairs"], *finite]
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in integers):
        raise ValueError("Histories, validation, cutoff, and refit spacing must be positive integers")
    if not finite or len(set(finite)) != len(finite) or min(finite) < 3:
        raise ValueError("Finite histories must be unique and contain at least three pairs")
    initial, refit, validation = integers[:3]
    if initial < max(finite) + validation:
        raise ValueError("First cutoff must provide max finite history plus validation")
    histories = [(str(length), length) for length in finite]
    if settings.get("include_expanding_control", True):
        histories.append(("expanding", None))
    for policy in declared:
        _penalties(policy, part["tuning"])
    return declared, targets, small, calendar, part["tuning"], initial, refit, validation, histories


def run_stage(
    datasets: dict[str, ForecastDataset], config: dict, stage: str = "development",
    progress: Callable[[dict], Any] | None = None,
) -> tuple[pd.DataFrame, list[dict], dict]:
    """Run one phase of the original 572+13k schedule, independently replayable."""
    started = perf_counter()
    if stage not in {"development", "final"}:
        raise ValueError("stage must be 'development' or 'final'")
    if not datasets:
        raise ValueError("At least one common-calendar weighting is required")
    declared, targets, small, calendar, tuning_settings, initial, refit, validation, histories = _configuration(config)
    first = next(iter(datasets.values()))
    if initial >= len(first.X):
        raise ValueError("No forecast pairs remain after the first cutoff")
    development_end = pd.Timestamp(calendar["development_response_end"])
    final_start, final_end = (pd.Timestamp(calendar[key]) for key in ("new_final_response_start", "new_final_response_end"))
    if development_end >= final_start or final_start > final_end:
        raise ValueError("Development and final response intervals must be ordered and disjoint")
    phase = (first.response_dates <= development_end if stage == "development" else
             (first.response_dates >= final_start) & (first.response_dates <= final_end))
    blocks = [(cut, np.arange(cut, min(cut + refit, len(first.X))))
              for cut in range(initial, len(first.X), refit)]
    blocks = [(cut, rows[phase[rows]]) for cut, rows in blocks if phase[rows].any()]
    records, tuning_records, representations = [], [], {}
    per_weighting, completed = {}, 0
    for weighting, dataset in datasets.items():
        weight_started = perf_counter()
        if not dataset.origin_dates.equals(first.origin_dates) or not dataset.response_dates.equals(first.response_dates):
            raise ValueError("All weightings must have identical origin/response dates")
        if tuple(dataset.asset_names) != tuple(first.asset_names):
            raise ValueError("All weightings must preserve the same canonical source column order")
        if not set(small).issubset(dataset.asset_names):
            raise ValueError("The declared named small panel is absent")
        if not ((dataset.response_dates - dataset.origin_dates) == pd.Timedelta(days=7)).all():
            raise ValueError("Responses must be exactly seven calendar days after origins")
        if not dataset.origin_dates.is_monotonic_increasing or dataset.origin_dates.has_duplicates:
            raise ValueError("Origin dates must be unique and chronological")
        for cut, test_rows in blocks:
            inner_stop = cut - validation
            if not (dataset.response_dates[:cut] <= dataset.origin_dates[cut]).all():
                raise AssertionError("Outer fitting contains an unavailable response")
            if not (dataset.response_dates[:inner_stop] <= dataset.origin_dates[inner_stop]).all():
                raise AssertionError("Inner fitting contains an unavailable response")
            validation_rows = np.arange(inner_stop, cut)
            for history_label, length in histories:
                inner_start = 0 if length is None else inner_stop - length
                outer_start = 0 if length is None else cut - length
                for target in targets:
                    ti = dataset.asset_names.index(target)
                    for policy in declared:
                        measurements, outcomes = _members(policy, target, dataset.asset_names, small)
                        scores = []
                        for penalty in _penalties(policy, tuning_settings):
                            fitted = _fit_window(
                                policy, penalty, dataset, target, measurements, outcomes,
                                inner_start, inner_stop, inner_stop, representations,
                                (weighting, cut, "inner", measurements), tuning_settings,
                            )
                            prediction = _predict(policy, fitted, dataset, target, measurements, outcomes, validation_rows)
                            scores.append(dict(penalty=penalty, validation_mse=mse(dataset.Y[validation_rows, ti], prediction)))
                        chosen = min(scores, key=lambda item: item["validation_mse"])
                        penalty = chosen["penalty"]
                        fitted = _fit_window(
                            policy, penalty, dataset, target, measurements, outcomes,
                            outer_start, cut, cut, representations,
                            (weighting, cut, "outer", measurements), tuning_settings,
                        )
                        prediction = _predict(policy, fitted, dataset, target, measurements, outcomes, test_rows)
                        if not np.isfinite(prediction).all():
                            raise ValueError("A declared policy produced a nonfinite forecast")
                        uses_pca = policy["method"] in FACTOR_METHODS
                        duplicate = policy["method"] == "persistence"
                        tuning_records.append(dict(
                            weighting=weighting, target=target, stage=stage, history=history_label, **policy,
                            refit_index=cut, refit_origin=dataset.origin_dates[cut].date().isoformat(),
                            inner_coef_start=inner_start, inner_coef_stop=inner_stop,
                            outer_coef_start=outer_start, outer_coef_stop=cut,
                            inner_pca_start=0 if uses_pca else None,
                            inner_pca_stop=inner_stop if uses_pca else None,
                            outer_pca_start=0 if uses_pca else None, outer_pca_stop=cut if uses_pca else None,
                            inner_coefficient_first_origin=dataset.origin_dates[inner_start].date().isoformat(),
                            inner_coefficient_last_response=dataset.response_dates[inner_stop - 1].date().isoformat(),
                            outer_coefficient_first_origin=dataset.origin_dates[outer_start].date().isoformat(),
                            outer_coefficient_last_response=dataset.response_dates[cut - 1].date().isoformat(),
                            validation_first_origin=dataset.origin_dates[inner_stop].date().isoformat(),
                            validation_last_response=dataset.response_dates[cut - 1].date().isoformat(),
                            measurement_assets=list(measurements), outcome_assets=list(outcomes),
                            candidate_scores=scores, chosen_penalty=penalty, validation_mse=chosen["validation_mse"],
                            persistence_duplicate_across_histories=duplicate,
                        ))
                        for index, forecast in zip(test_rows, prediction, strict=True):
                            actual = float(dataset.Y[index, ti])
                            error = actual - float(forecast)
                            records.append(dict(
                                weighting=weighting, target=target, history=history_label, **policy,
                                n_measurements=len(measurements), n_outcomes=len(outcomes),
                                origin_index=int(index), origin_date=dataset.origin_dates[index].date().isoformat(),
                                response_date=dataset.response_dates[index].date().isoformat(),
                                refit_index=cut, penalty=penalty, prediction=float(forecast), actual=actual,
                                squared_error=error**2, absolute_error=abs(error), stage=stage,
                                coefficient_train_start=outer_start, coefficient_train_stop=cut,
                                pca_train_start=0 if uses_pca else None, pca_train_stop=cut if uses_pca else None,
                                persistence_duplicate_across_histories=duplicate,
                            ))
            completed += 1
            if progress is not None:
                progress(dict(weighting=weighting, stage=stage, refit_index=cut, n_origins=len(test_rows),
                              completed_blocks=completed, total_blocks=len(blocks) * len(datasets),
                              elapsed_seconds=perf_counter() - started))
        per_weighting[weighting] = perf_counter() - weight_started
    timing = dict(elapsed_seconds=perf_counter() - started, blocks=completed, prediction_rows=len(records),
                  tuning_rows=len(tuning_records), pca_fits=len(representations),
                  per_weighting_seconds=per_weighting, histories=[label for label, _ in histories])
    return pd.DataFrame.from_records(records, columns=PREDICTION_COLUMNS), tuning_records, timing
