"""Calendar-aligned weekly proxies and strictly causal forecast pairs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .data import validate_daily_returns


@dataclass(frozen=True)
class WeeklyFeaturePanels:
    """Calendar-preserving weekly features from daily decimal returns.

    Volatility is the square root of the weekly sum of squared returns, without
    annualization. Histories are trailing arithmetic means of log variance,
    including the current week, and require every week in the window. Counts
    describe observed daily inputs even when too few exist for a valid proxy.
    """

    variance: pd.DataFrame
    volatility: pd.DataFrame
    log_variance: pd.DataFrame
    log_variance_mean_4w: pd.DataFrame
    log_variance_mean_12w: pd.DataFrame
    observed_daily_counts: pd.DataFrame

    def as_dict(self) -> dict[str, pd.DataFrame]:
        """Return the six named panels without copying their data."""
        return {
            "variance": self.variance,
            "volatility": self.volatility,
            "log_variance": self.log_variance,
            "log_variance_mean_4w": self.log_variance_mean_4w,
            "log_variance_mean_12w": self.log_variance_mean_12w,
            "observed_daily_counts": self.observed_daily_counts,
        }


@dataclass(frozen=True)
class ForecastDataset:
    """One common sample shared by every forecast method.

    ``X`` contains origin-week panel log variance proxies, ``Y`` the next-week
    panel, and ``local_all`` all assets' trailing 1/4/12-week log-proxy means.
    ``local`` selects those three controls for the named target. All arrays are
    finite, and response dates are exactly seven days after origin dates.
    """

    X: np.ndarray
    Y: np.ndarray
    local: np.ndarray
    local_all: np.ndarray
    origin_dates: pd.DatetimeIndex
    response_dates: pd.DatetimeIndex
    asset_names: tuple[str, ...]
    target_name: str
    report: dict[str, Any]

    @property
    def target_index(self) -> int:
        return self.asset_names.index(self.target_name)

    @property
    def y(self) -> np.ndarray:
        """The target's next-week log proxy, a length-T convenience view."""
        return self.Y[:, self.target_index]


def weekly_variance(returns: pd.DataFrame, *, min_week_obs: int = 3) -> pd.DataFrame:
    """Sum squared daily decimal returns in Friday-ending calendar weeks.

    Every intervening calendar week is retained. Each asset/week needs at least
    ``min_week_obs`` observed returns; insufficient observations produce NaN.
    This is a close-to-close variance proxy, not intraday realized variance.
    """
    validate_daily_returns(returns)
    if not isinstance(min_week_obs, int) or isinstance(min_week_obs, bool) or min_week_obs < 1:
        raise ValueError("min_week_obs must be a positive integer.")
    return returns.pow(2).resample("W-FRI", closed="right", label="right").sum(min_count=min_week_obs)


def build_weekly_feature_panels(
    returns: pd.DataFrame,
    *,
    log_offset: float = 1e-8,
    min_week_obs: int = 3,
) -> WeeklyFeaturePanels:
    """Construct weekly proxies and causal histories without dropping any week.

    Friday-ending weeks are right-closed and right-labeled. Partial endpoint
    weeks follow the same minimum-observation rule as all other weeks. Missing
    values are never filled, and wholly absent weeks have zero daily counts.
    """
    if not np.isfinite(log_offset) or log_offset <= 0:
        raise ValueError("log_offset must be finite and strictly positive.")
    variance = weekly_variance(returns, min_week_obs=min_week_obs)
    log_variance = np.log(variance + log_offset)
    return WeeklyFeaturePanels(
        variance=variance,
        volatility=np.sqrt(variance),
        log_variance=log_variance,
        log_variance_mean_4w=log_variance.rolling(4, min_periods=4).mean(),
        log_variance_mean_12w=log_variance.rolling(12, min_periods=12).mean(),
        observed_daily_counts=returns.resample("W-FRI", closed="right", label="right").count(),
    )


def build_weekly_dataset(
    returns: pd.DataFrame,
    *,
    target: str,
    log_offset: float = 1e-8,
    min_week_obs: int = 3,
) -> ForecastDataset:
    """Construct next-calendar-week forecasts using only origin-or-earlier data.

    Trailing controls average weekly ``log(V + log_offset)`` over 1, 4 and 12
    weeks; all weeks in each history must be observed. A single common-case
    mask requires finite origin predictors, next-week outcomes, and all assets'
    controls. Dates with holes are discarded only after creating calendar-aligned
    lags, so deletion never turns a later week into the next-week response.
    """
    panels = build_weekly_feature_panels(
        returns, log_offset=log_offset, min_week_obs=min_week_obs
    )
    weekly = panels.variance
    if target not in weekly.columns:
        raise ValueError(f"Target {target!r} is not an asset column.")
    log_weekly = panels.log_variance
    next_week = log_weekly.shift(-1)
    histories = [log_weekly, panels.log_variance_mean_4w, panels.log_variance_mean_12w]
    X_all = log_weekly.to_numpy(dtype=float)
    Y_all = next_week.to_numpy(dtype=float)
    local_all = np.stack([frame.to_numpy(dtype=float) for frame in histories], axis=2)
    valid_origin = np.isfinite(X_all).all(axis=1)
    valid_response = np.isfinite(Y_all).all(axis=1)
    valid_history = np.isfinite(local_all).all(axis=(1, 2))
    common = valid_origin & valid_response & valid_history
    asset_names = tuple(weekly.columns)
    target_index = asset_names.index(target)
    dates = weekly.index
    if not common.any():
        raise ValueError("No complete forecast pairs remain after 12-week histories and next-week alignment.")
    report: dict[str, Any] = {
        "frequency": "W-FRI",
        "variance_proxy": "sum_of_squared_daily_decimal_returns",
        "min_week_obs": min_week_obs,
        "log_offset": float(log_offset),
        "history_windows_weeks": [1, 4, 12],
        "history_definition": "arithmetic_mean_of_weekly_log_proxy",
        "target": target,
        "asset_names": list(asset_names),
        "calendar_weeks": int(len(weekly)),
        "weekly_missing_by_asset": {name: int(count) for name, count in weekly.isna().sum().items()},
        "candidate_origins": int(len(weekly) - 1),
        "common_complete_pairs": int(common.sum()),
        "dropped_origins": int(len(weekly) - 1 - int(common.sum())),
        "final_week_without_response": 1,
        "invalid_origin_predictors": int((~valid_origin[:-1]).sum()),
        "invalid_next_week_outcomes": int((~valid_response[:-1]).sum()),
        "invalid_own_history_controls": int((~valid_history[:-1]).sum()),
        "drop_counts_overlap": True,
        "first_origin": dates[common][0].date().isoformat(),
        "last_origin": dates[common][-1].date().isoformat(),
        "first_response": (dates[common][0] + pd.Timedelta(days=7)).date().isoformat(),
        "last_response": (dates[common][-1] + pd.Timedelta(days=7)).date().isoformat(),
        "missingness_policy": "calendar_grid_then_common_complete_case_no_fill",
        "source": dict(returns.attrs),
    }
    return ForecastDataset(
        X=X_all[common],
        Y=Y_all[common],
        local=local_all[common, target_index, :],
        local_all=local_all[common],
        origin_dates=dates[common],
        response_dates=dates[common] + pd.Timedelta(days=7),
        asset_names=asset_names,
        target_name=target,
        report=report,
    )
