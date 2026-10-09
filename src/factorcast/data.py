"""Validated, local-only daily-return input for the empirical experiments."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

ReturnUnits = Literal["decimal", "percent"]


def validate_daily_returns(returns: pd.DataFrame) -> None:
    """Reject invalid daily panels; NaN values are allowed and never filled."""
    if returns.empty or len(returns.columns) == 0:
        raise ValueError("Daily returns must contain at least one date and one asset.")
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise ValueError("Daily returns require a DatetimeIndex.")
    if returns.index.hasnans or returns.index.tz is not None:
        raise ValueError("Daily dates must be valid, timezone-free calendar dates.")
    if not returns.index.equals(returns.index.normalize()):
        raise ValueError("Daily dates must not include time-of-day values.")
    if returns.index.has_duplicates or not returns.index.is_monotonic_increasing:
        raise ValueError("Daily dates must be unique and strictly chronological.")
    if returns.columns.has_duplicates or any(
        not isinstance(name, str) or not name.strip() for name in returns.columns
    ):
        raise ValueError("Asset names must be unique, nonempty strings.")
    if any(not pd.api.types.is_numeric_dtype(dtype) for dtype in returns.dtypes):
        raise ValueError("Every asset return column must be numeric.")
    values = returns.to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("Daily returns cannot contain infinite values.")


def load_daily_returns(path: str | Path, *, units: ReturnUnits) -> pd.DataFrame:
    """Load ``date,asset_1,...`` CSV data and return decimal daily returns.

    The units argument is mandatory. Missing numeric cells remain NaN. Known
    French-library missing-value sentinels are rejected before unit conversion,
    so a manual adapter must deliberately convert them to empty cells first.
    Dates are required to be unique and already ordered; input is never sorted.
    Source provenance and missingness are attached in ``DataFrame.attrs``.
    """
    if units not in {"decimal", "percent"}:
        raise ValueError("units must be explicitly 'decimal' or 'percent'.")
    source = Path(path).expanduser().resolve()
    with source.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle), [])
    columns = [name.strip() for name in header]
    if "date" not in columns or len(columns) < 2:
        raise ValueError("CSV must contain a date column and at least one asset column.")
    if len(set(columns)) != len(columns) or any(not name for name in columns):
        raise ValueError("CSV column names must be unique and nonempty.")
    frame = pd.read_csv(source, encoding="utf-8-sig", dtype=str)
    frame.columns = columns
    try:
        dates = pd.DatetimeIndex(pd.to_datetime(frame.pop("date"), errors="raise"))
    except (TypeError, ValueError) as exc:
        raise ValueError("The date column must contain parseable calendar dates.") from exc
    try:
        numeric = frame.apply(pd.to_numeric, errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Every asset return column must be numeric or missing.") from exc
    values = numeric.to_numpy(dtype=float)
    if any(np.isclose(values, sentinel, rtol=0, atol=1e-10).any() for sentinel in (-99.99, -999.0)):
        raise ValueError("Known missing-value sentinel found; convert -99.99/-999 to empty cells explicitly.")
    numeric.index = dates
    numeric.index.name = "date"
    validate_daily_returns(numeric)
    if units == "percent":
        numeric = numeric / 100.0
    numeric.attrs.update(
        source_path=str(source),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_units=units,
        return_units="decimal",
        daily_rows=int(len(numeric)),
        daily_missing_by_asset={name: int(count) for name, count in numeric.isna().sum().items()},
    )
    return numeric
