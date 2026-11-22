"""Trends over time, and a simple forecast.

Monthly numbers jump about, so a rolling average smooths them out: each
point is the average of the last few months, like judging your weight by
the week instead of by the day.

The forecasts are simple on purpose. There are two, behind a Forecaster
base class, and backtest() checks how wrong each would have been on months
we already know. A forecast you haven't checked is just a guess.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .exceptions import ValidationError

MONEY_COLUMNS = ("revenue_pence", "profit_pence", "cost_pence", "quantity")


def monthly_series(sales: pd.DataFrame, column: str = "revenue_pence") -> pd.Series:
    """One total per month. Months with no sales show 0 rather than being skipped."""
    if column not in MONEY_COLUMNS:
        raise ValidationError(f"Can't track {column!r}. Try one of: {', '.join(MONEY_COLUMNS)}.")
    if sales.empty:
        return pd.Series(dtype="float64", index=pd.PeriodIndex([], freq="M"), name=column)
    totals = sales.groupby("month")[column].sum()
    every_month = pd.period_range(totals.index.min(), totals.index.max(), freq="M")
    return totals.reindex(every_month, fill_value=0).astype("float64").rename(column)


def rolling_average(series: pd.Series, window: int = 3) -> pd.Series:
    """The average of each month and the ones before it. The first few are blank (NaN)."""
    if window < 1:
        raise ValidationError("window must be at least 1.")
    return series.rolling(window, min_periods=window).mean()


def growth(series: pd.Series) -> pd.Series:
    """How much each month changed from the one before, as a fraction. 0.1 means up 10%."""
    before = series.shift(1)
    return (series - before) / before.where(before != 0)


class Forecaster(ABC):
    """Guesses the next few months from the months so far."""

    name = ""

    @abstractmethod
    def predict(self, history: pd.Series, months: int) -> pd.Series:
        """The next `months` values, labelled with their months. Never below 0."""

    @staticmethod
    def future_index(history: pd.Series, months: int) -> pd.PeriodIndex:
        if months < 1:
            raise ValidationError("months must be at least 1.")
        if history.empty:
            raise ValidationError("A forecast needs some history.")
        return pd.period_range(history.index[-1] + 1, periods=months, freq="M")


class LinearTrend(Forecaster):
    """Draws the straight line that best fits the past, and carries it on."""

    name = "Straight line trend"

    def predict(self, history: pd.Series, months: int) -> pd.Series:
        index = self.future_index(history, months)
        if len(history) < 2:
            return pd.Series(float(history.iloc[-1]), index=index)
        x = np.arange(len(history))
        slope, start = np.polyfit(x, history.to_numpy(dtype=float), 1)
        future = start + slope * np.arange(len(history), len(history) + months)
        return pd.Series(np.clip(future, 0, None), index=index)


class SeasonalNaive(Forecaster):
    """Next October will be like last October, plus however much the shop has grown.

    Growth is the last 12 months compared with the 12 before. It needs a
    full year of history to work.
    """

    name = "Same month last year, plus growth"

    def predict(self, history: pd.Series, months: int) -> pd.Series:
        index = self.future_index(history, months)
        if len(history) < 12:
            raise ValidationError("This forecast needs at least 12 months of history.")
        growth_rate = 1.0
        if len(history) >= 24:
            last, before = history.iloc[-12:].sum(), history.iloc[-24:-12].sum()
            growth_rate = last / before if before else 1.0
        known = history.to_dict()
        values = []
        for month in index:
            last_year = month - 12
            if last_year in known:
                values.append(known[last_year] * growth_rate)
            else:
                # More than a year ahead: grow this month's forecast from a year before.
                values.append(values[-12] * growth_rate)
        return pd.Series(np.clip(values, 0, None), index=index)


@dataclass(frozen=True)
class Backtest:
    """How a forecaster did on months we already knew the answer to."""

    name: str
    months: int
    average_error: float

    def text(self) -> str:
        return f"{self.name}: off by {self.average_error:.1%} on average over {self.months} months"


def backtest(forecaster: Forecaster, history: pd.Series, holdout: int = 6) -> Backtest:
    """Hide the last `holdout` months, forecast them, and see how far off it was.

    It's like a practice exam: the answers exist, we just don't look until
    the forecast is written.
    """
    if holdout < 1 or holdout >= len(history):
        raise ValidationError("holdout must be at least 1 and less than the months of history.")
    known, actual = history.iloc[:-holdout], history.iloc[-holdout:]
    guess = forecaster.predict(known, holdout)
    real = actual.to_numpy(dtype=float)
    errors = np.abs(guess.to_numpy() - real) / np.where(real == 0, np.nan, real)
    return Backtest(forecaster.name, holdout, float(np.nanmean(errors)))
