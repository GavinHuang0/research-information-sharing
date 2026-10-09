"""Chronological outer evaluation and historical inner validation."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ForecastBlock:
    train: slice
    validation: slice
    history: slice
    test: slice


def forecast_blocks(n_rows, initial_train, validation_size, test_size, refit_every):
    """Each row is an origin/next-period outcome pair.

    At origin t, outcomes in rows s<t are already realized. Inner transforms
    are fitted on train only; final models are refitted on history. Outer
    outcomes may enter history only at a later refit, after realization.
    """
    values = [n_rows, initial_train, validation_size, test_size, refit_every]
    if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in values):
        raise ValueError("Split sizes must be positive integers")
    if validation_size >= initial_train or initial_train + test_size > n_rows:
        raise ValueError("Need initial_train > validation_size and enough test rows")
    stop = initial_train + test_size
    for origin in range(initial_train, stop, refit_every):
        yield ForecastBlock(
            train=slice(0, origin - validation_size),
            validation=slice(origin - validation_size, origin),
            history=slice(0, origin),
            test=slice(origin, min(origin + refit_every, stop)),
        )


def mse(actual, forecast):
    actual, forecast = np.asarray(actual), np.asarray(forecast)
    if actual.shape != forecast.shape or actual.size == 0:
        raise ValueError("Loss inputs must be nonempty and have identical shapes")
    if not np.isfinite(actual).all() or not np.isfinite(forecast).all():
        raise ValueError("Loss inputs must be finite")
    return float(np.mean((actual - forecast) ** 2))


def factor_diagnostics(training_scores, training_factors, test_scores, test_factors):
    """Align using historical true factors; report test error, never tune on it.

    A linear map handles PCA signs, scale and rotations. This is a simulation
    diagnostic, not proof of recovery of a unique economically named factor.
    """
    design = np.column_stack([np.ones(len(training_scores)), training_scores])
    alignment = np.linalg.lstsq(design, training_factors, rcond=None)[0]
    aligned = np.column_stack([np.ones(len(test_scores)), test_scores]) @ alignment
    return mse(test_factors, aligned)
