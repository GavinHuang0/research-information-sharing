"""Fixed-membership industry pilot with chronological, target-only tuning.

Development and final runs replay one refit schedule. No fitted state or test
loss is passed from one phase to another, and the final phase can run alone.
"""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from .evaluation import mse
from .features import ForecastDataset, build_weekly_dataset
from .models import DirectForecaster, FactorForecaster, PCARepresentation, PLSForecaster

S = ("Food", "Mach", "Banks", "Oil", "Util", "Hlth")
FACTOR_METHODS = ("factor_separate", "factor_pooled", "factor_partial")
PREDICTION_COLUMNS = [
    "weighting", "target", "policy_id", "method", "measurement_panel", "outcome_panel",
    "n_measurements", "n_outcomes", "n_factors", "origin_index", "origin_date",
    "response_date", "refit_index", "penalty", "prediction", "actual", "squared_error",
    "absolute_error", "stage",
]


def _design(config: dict) -> tuple[tuple[str, ...], tuple[str, ...]]:
    design = config.get("design", {})
    targets = tuple(design.get("targets", S))
    small = tuple(design.get("small_panel", S))
    for label, names in (("targets", targets), ("small_panel", small)):
        if not names or len(set(names)) != len(names) or any(not isinstance(x, str) or not x for x in names):
            raise ValueError(f"{label} must contain unique nonempty asset names")
    if not set(targets).issubset(small):
        raise ValueError("Every target must belong to the fixed small panel")
    return targets, small


def policies(config: dict) -> list[dict]:
    """The 18 declared policies; separate regression has no redundant donors."""
    _design(config)
    k = config.get("experiment", {}).get("factor_count", 2)
    if k != 2 or isinstance(k, bool):
        raise ValueError("The fixed pilot requires factor_count = 2")
    result = []

    def add(method, measurement, outcome):
        result.append(dict(
            policy_id=f"{method}__M-{measurement}__O-{outcome}", method=method,
            measurement_panel=measurement, outcome_panel=outcome,
            n_factors=k if method in FACTOR_METHODS or method == "pls" else 0,
        ))

    for measurement in ("S", "all"):
        add("factor_separate", measurement, "target")
        for method in ("factor_pooled", "factor_partial"):
            for outcome in ("S", "all"):
                add(method, measurement, outcome)
        for method in ("ridge", "elasticnet", "pls"):
            add(method, measurement, "target")
    add("local_history", "none", "target")
    add("persistence", "none", "target")
    return result


def prepare_panels(
    returns_by_weighting: dict[str, pd.DataFrame], config: dict
) -> tuple[dict[str, ForecastDataset], dict]:
    """Warm up all columns first, then intersect pairs and apply calendar bounds.

    The first input's column order is canonical. Other weightings are aligned
    by asset name, never by position. Small synthetic panels are supported for
    verification; the empirical inputs contain the full 48 industries.
    """
    targets, small = _design(config)
    if not returns_by_weighting:
        raise ValueError("At least one return weighting is required")
    canonical = tuple(next(iter(returns_by_weighting.values())).columns)
    if not set(small).issubset(canonical):
        raise ValueError("The fixed small panel is missing from the source columns")
    data = config.get("data", {})
    datasets = {}
    for weighting, returns in returns_by_weighting.items():
        if len(returns.columns) != len(canonical) or set(returns.columns) != set(canonical):
            raise ValueError("Every weighting must contain the same industry membership")
        datasets[weighting] = build_weekly_dataset(
            returns.loc[:, list(canonical)], target=targets[0],
            log_offset=data.get("log_offset", 1e-8), min_week_obs=data.get("min_week_obs", 3),
        )
    shared = next(iter(datasets.values())).origin_dates
    for dataset in datasets.values():
        if not ((dataset.response_dates - dataset.origin_dates) == pd.Timedelta(days=7)).all():
            raise ValueError("Every response must be exactly one calendar week after its origin")
        shared = shared.intersection(dataset.origin_dates, sort=False)
    calendar = config.get("calendar", {})
    origin_start = pd.Timestamp(calendar.get("origin_start", "2000-01-01"))
    response_end = pd.Timestamp(calendar.get("response_end", "2024-12-31"))
    final_start = pd.Timestamp(calendar.get("final_response_start", "2022-01-01"))
    common_count = len(shared)
    selected = shared[(shared >= origin_start) & (shared + pd.Timedelta(days=7) <= response_end)]
    if selected.empty:
        raise ValueError("No common forecast pairs remain inside the declared calendar")
    source_reports = {weighting: dataset.report for weighting, dataset in datasets.items()}
    for weighting, dataset in datasets.items():
        indices = dataset.origin_dates.get_indexer(selected)
        report = dict(dataset.report, pilot_common_pairs=len(selected),
                      pilot_origin_start=origin_start.date().isoformat(),
                      pilot_response_end=response_end.date().isoformat())
        datasets[weighting] = replace(
            dataset, X=dataset.X[indices], Y=dataset.Y[indices],
            local_all=dataset.local_all[indices], local=dataset.local[indices],
            origin_dates=dataset.origin_dates[indices], response_dates=dataset.response_dates[indices],
            report=report,
        )
    response_dates = selected + pd.Timedelta(days=7)
    report = dict(
        canonical_asset_names=list(canonical), targets=list(targets), small_panel=list(small),
        alignment="all_columns_complete_then_weighting_intersection_then_calendar_bounds",
        common_pairs_before_calendar=common_count, common_pairs=len(selected),
        origin_start=origin_start.date().isoformat(), response_end=response_end.date().isoformat(),
        final_response_start=final_start.date().isoformat(),
        first_origin=selected[0].date().isoformat(), last_origin=selected[-1].date().isoformat(),
        first_response=response_dates[0].date().isoformat(), last_response=response_dates[-1].date().isoformat(),
        development_pairs=int((response_dates < final_start).sum()),
        final_pairs=int((response_dates >= final_start).sum()), weighting_reports=source_reports,
    )
    return datasets, report


def _members(policy, target, names, small):
    measurements = (() if policy["measurement_panel"] == "none" else
                    small if policy["measurement_panel"] == "S" else names)
    outcomes = ((target,) if policy["outcome_panel"] == "target" else
                small if policy["outcome_panel"] == "S" else names)
    return tuple(measurements), tuple(outcomes)


def _penalties(policy, settings):
    key = {"factor_partial": "pooling_penalties", "ridge": "ridge_penalties",
           "elasticnet": "elasticnet_penalties"}.get(policy["method"])
    values = [0.0] if key is None else settings[key]
    if not values or any(not np.isfinite(v) or v < 0 for v in values):
        raise ValueError(f"{key or 'penalties'} must contain finite nonnegative penalties")
    return [float(v) for v in values]


def _fit(policy, penalty, dataset, target, measurements, outcomes, stop, representations, cache_key):
    names = dataset.asset_names
    mi, oi = [names.index(name) for name in measurements], [names.index(name) for name in outcomes]
    target_index = names.index(target)
    x = dataset.X[:stop, mi]
    y = dataset.Y[:stop, oi]
    controls = dataset.local_all[:stop, oi, :]
    method = policy["method"]
    if method == "persistence":
        return None
    if method == "local_history":
        return LinearRegression().fit(dataset.local_all[:stop, target_index, :], dataset.Y[:stop, target_index])
    if method in FACTOR_METHODS:
        if cache_key not in representations:
            representations[cache_key] = PCARepresentation(policy["n_factors"]).fit(x)
        return FactorForecaster(
            n_factors=policy["n_factors"], pooling=method.removeprefix("factor_"),
            penalty=penalty, representation=representations[cache_key],
        ).fit(x, y, target=outcomes.index(target), local=controls)
    model = (PLSForecaster(policy["n_factors"]) if method == "pls" else
             DirectForecaster(method=method, penalty=penalty))
    design = np.column_stack([np.ones(stop), controls[:, 0, :]])
    x_projection = np.linalg.lstsq(design, x, rcond=None)[0]
    y_projection = np.linalg.lstsq(design, y[:, 0], rcond=None)[0]
    residual_x = x - design @ x_projection
    mask = residual_x.std(axis=0) > 1e-10 * np.maximum(x.std(axis=0), 1.0)
    if method == "pls" and policy["n_factors"] > int(mask.sum()):
        raise ValueError("Fixed PLS dimension exceeds nonconstant predictors after local FWL")
    if mask.any():
        residual_y = y[:, 0] - design @ y_projection
        model.fit(residual_x[:, mask], residual_y)
        if method == "elasticnet" and penalty > 0:
            # Converge the same normalized objective tightly enough that a
            # source-column permutation cannot alter the policy comparison.
            model.regressor_.set_params(tol=1e-10, max_iter=100000)
            model.regressor_.fit(model.feature_scaler_.transform(residual_x[:, mask]), residual_y)
    return model, x_projection, y_projection, mask


def _predict(policy, model, dataset, target, measurements, outcomes, rows):
    names = dataset.asset_names
    mi, oi = [names.index(name) for name in measurements], [names.index(name) for name in outcomes]
    x = dataset.X[rows][:, mi]
    local = dataset.local_all[rows][:, oi, :]
    target_index = names.index(target)
    method = policy["method"]
    if method == "persistence":
        return dataset.local_all[rows, target_index, 0]
    if method == "local_history":
        return model.predict(dataset.local_all[rows, target_index, :])
    if method in FACTOR_METHODS:
        return model.predict(x, local=local)
    fitted, x_projection, y_projection, mask = model
    design = np.column_stack([np.ones(len(x)), local[:, 0, :]])
    prediction = design @ y_projection
    if mask.any():
        prediction = prediction + fitted.predict((x - design @ x_projection)[:, mask])
    return prediction


def run_stage(
    datasets: dict[str, ForecastDataset], config: dict, stage: str = "development",
    progress: Callable[[dict], Any] | None = None,
) -> tuple[pd.DataFrame, list[dict], dict]:
    """Run only one response-date phase on the globally anchored refit grid."""
    started = perf_counter()
    if stage not in {"development", "final"}:
        raise ValueError("stage must be 'development' or 'final'")
    if not datasets:
        raise ValueError("At least one prepared weighting is required")
    targets, small = _design(config)
    declared = policies(config)
    settings = config["experiment"]
    initial, validation, refit = (settings[k] for k in ("initial_train", "validation_size", "refit_every"))
    if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in (initial, validation, refit)):
        raise ValueError("Initial history, validation, and refit sizes must be positive integers")
    if initial - validation < 3:
        raise ValueError("Inner training needs at least three pairs")
    first = next(iter(datasets.values()))
    if initial >= len(first.X):
        raise ValueError("Not enough common pairs after the initial history")
    boundary = pd.Timestamp(config.get("calendar", {}).get("final_response_start", "2022-01-01"))
    phase = first.response_dates < boundary if stage == "development" else first.response_dates >= boundary
    blocks = [(cut, np.arange(cut, min(cut + refit, len(first.X))))
              for cut in range(initial, len(first.X), refit)]
    blocks = [(cut, rows[phase[rows]]) for cut, rows in blocks if phase[rows].any()]
    records, tuning, representations = [], [], {}
    per_weighting, completed = {}, 0
    for weighting, dataset in datasets.items():
        weight_started = perf_counter()
        if (not dataset.origin_dates.equals(first.origin_dates) or
                not dataset.response_dates.equals(first.response_dates)):
            raise ValueError("All prepared weightings must use identical origin/response pairs")
        if not set(small).issubset(dataset.asset_names):
            raise ValueError("The fixed panel is missing from the prepared dataset")
        if not ((dataset.response_dates - dataset.origin_dates) == pd.Timedelta(days=7)).all():
            raise ValueError("Every response must be exactly one calendar week after its origin")
        for cut, test_rows in blocks:
            inner_stop = cut - validation
            if not (dataset.response_dates[:cut] <= dataset.origin_dates[cut]).all():
                raise AssertionError("Outer training contains outcomes unavailable at refit origin")
            if not (dataset.response_dates[:inner_stop] <= dataset.origin_dates[inner_stop]).all():
                raise AssertionError("Inner training contains outcomes unavailable at validation origin")
            validation_rows = np.arange(inner_stop, cut)
            for target in targets:
                target_index = dataset.asset_names.index(target)
                for policy in declared:
                    measurements, outcomes = _members(policy, target, dataset.asset_names, small)
                    scores = []
                    for penalty in _penalties(policy, settings):
                        model = _fit(policy, penalty, dataset, target, measurements, outcomes,
                                     inner_stop, representations, (weighting, cut, "inner", measurements))
                        prediction = _predict(policy, model, dataset, target, measurements, outcomes, validation_rows)
                        scores.append(dict(penalty=penalty, validation_mse=mse(dataset.Y[validation_rows, target_index], prediction)))
                    chosen = min(scores, key=lambda item: item["validation_mse"])
                    penalty = chosen["penalty"]
                    model = _fit(policy, penalty, dataset, target, measurements, outcomes,
                                 cut, representations, (weighting, cut, "outer", measurements))
                    prediction = _predict(policy, model, dataset, target, measurements, outcomes, test_rows)
                    if not np.isfinite(prediction).all():
                        raise ValueError("A declared policy produced a nonfinite forecast")
                    tuning.append(dict(
                        weighting=weighting, target=target, stage=stage, **policy,
                        refit_index=cut, refit_origin=dataset.origin_dates[cut].date().isoformat(),
                        inner_train_stop=inner_stop, history_stop=cut,
                        inner_train_last_response=dataset.response_dates[inner_stop - 1].date().isoformat(),
                        validation_first_origin=dataset.origin_dates[inner_stop].date().isoformat(),
                        validation_last_response=dataset.response_dates[cut - 1].date().isoformat(),
                        history_last_response=dataset.response_dates[cut - 1].date().isoformat(),
                        measurement_assets=list(measurements), outcome_assets=list(outcomes),
                        candidate_scores=scores, chosen_penalty=penalty,
                        validation_mse=chosen["validation_mse"],
                    ))
                    for index, forecast in zip(test_rows, prediction, strict=True):
                        actual = float(dataset.Y[index, target_index])
                        error = actual - float(forecast)
                        records.append(dict(
                            weighting=weighting, target=target, **policy,
                            n_measurements=len(measurements), n_outcomes=len(outcomes),
                            origin_index=int(index), origin_date=dataset.origin_dates[index].date().isoformat(),
                            response_date=dataset.response_dates[index].date().isoformat(),
                            refit_index=cut, penalty=penalty, prediction=float(forecast), actual=actual,
                            squared_error=error**2, absolute_error=abs(error), stage=stage,
                        ))
            completed += 1
            if progress is not None:
                progress(dict(weighting=weighting, stage=stage, refit_index=cut,
                              n_origins=len(test_rows), completed_blocks=completed,
                              total_blocks=len(blocks) * len(datasets), elapsed_seconds=perf_counter() - started))
        per_weighting[weighting] = perf_counter() - weight_started
    timing = dict(elapsed_seconds=perf_counter() - started, blocks=completed,
                  prediction_rows=len(records), pca_fits=len(representations),
                  per_weighting_seconds=per_weighting)
    return pd.DataFrame.from_records(records, columns=PREDICTION_COLUMNS), tuning, timing
