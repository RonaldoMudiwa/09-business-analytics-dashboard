"""Comparing one period with another.

"We took £30k in October" means little on its own. Is that good? Compared
with September, and with October last year, it suddenly means something.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from .exceptions import ValidationError
from .filters import DateRange
from .metrics import DEFAULT_METRICS, Metric
from .money import format_percent


@dataclass(frozen=True)
class Change:
    """One KPI in two periods, and how much it moved."""

    label: str
    current: float
    previous: float
    current_text: str
    previous_text: str
    is_rate: bool = False

    @property
    def difference(self) -> float:
        return self.current - self.previous

    @property
    def percent(self) -> float | None:
        """The change as a fraction of before. None if before was 0, because that can't be divided."""
        return self.difference / self.previous if self.previous else None

    def arrow(self) -> str:
        """▲ up, ▼ down, or ▬ no change."""
        return "▲" if self.difference > 0 else "▼" if self.difference < 0 else "▬"

    def percent_text(self) -> str:
        """e.g. '+18.4%'. Rates like the margin show percentage points instead.

        If the margin goes from 50% to 52%, saying "+4%" would confuse
        everyone. "+2.0 pts" says what really happened.
        """
        if self.is_rate:
            return f"{self.difference * 100:+.1f} pts"
        if self.percent is None:
            return "new"
        return ("+" if self.percent > 0 else "") + format_percent(self.percent)


def whole_dates(period: DateRange) -> tuple[pd.Timestamp, pd.Timestamp]:
    if period.start is None or period.end is None:
        raise ValidationError("Comparisons need a start and an end date.")
    return period.start, period.end


def previous_period(period: DateRange) -> DateRange:
    """The same number of days, straight before. Whole months give the whole month before."""
    start, end = whole_dates(period)
    if start.is_month_start and end.is_month_end:
        months = (end.to_period("M") - start.to_period("M")).n + 1
        first = start.to_period("M") - months
        return DateRange(first.start_time, (first + months - 1).end_time)
    days = (end - start).days + 1
    return DateRange(start - pd.Timedelta(days=days), start - pd.Timedelta(days=1))


def same_period_last_year(period: DateRange) -> DateRange:
    """e.g. October 2026 becomes October 2025. 29 February becomes 28 February."""
    start, end = whole_dates(period)
    year = pd.DateOffset(years=1)
    return DateRange(start - year, end - year)


def compare(sales: pd.DataFrame, current: DateRange, previous: DateRange,
            metrics: Sequence[Metric] = DEFAULT_METRICS) -> list[Change]:
    """Every metric in both periods."""
    now, before = current.apply(sales), previous.apply(sales)
    changes = []
    for metric in metrics:
        a, b = metric.compute(now), metric.compute(before)
        changes.append(Change(metric.label, a, b, metric.format(a), metric.format(b),
                              metric.is_rate))
    return changes


def latest_month(sales: pd.DataFrame) -> str:
    """The last month with any sales, like '2026-10'."""
    if sales.empty:
        raise ValidationError("There are no sales to compare.")
    return str(sales["month"].max())
