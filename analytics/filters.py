"""Filters for picking which sales to look at.

Each filter answers yes or no for every row. They can be joined like
sentences: & means "and", | means "or", ~ means "not".

    DateRange("2026-06-01", "2026-08-31") & IsOneOf("region", ["London"])

means "summer sales in London". It's like the filter buttons on a
shopping site, stacked on top of each other.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

import pandas as pd

from .exceptions import ValidationError


class SalesFilter(ABC):
    """Decides which rows to keep."""

    @abstractmethod
    def mask(self, sales: pd.DataFrame) -> pd.Series:
        """True for every row to keep."""

    @abstractmethod
    def describe(self) -> str:
        """A short description for reports, like 'region is London'."""

    def apply(self, sales: pd.DataFrame) -> pd.DataFrame:
        return sales[self.mask(sales)]

    def __and__(self, other: SalesFilter) -> SalesFilter:
        return AllOf(self, other)

    def __or__(self, other: SalesFilter) -> SalesFilter:
        return AnyOf(self, other)

    def __invert__(self) -> SalesFilter:
        return Not(self)


class Everything(SalesFilter):
    """Keeps every row. Used when no filter is asked for."""

    def mask(self, sales: pd.DataFrame) -> pd.Series:
        return pd.Series(True, index=sales.index)

    def describe(self) -> str:
        return "all sales"


def to_timestamp(value: str | pd.Timestamp, what: str) -> pd.Timestamp:
    try:
        return pd.Timestamp(value).normalize()
    except (ValueError, TypeError):
        raise ValidationError(f"{what} {value!r} isn't a date. Use YYYY-MM-DD.") from None


class DateRange(SalesFilter):
    """Sales from start to end, including both days. Either end can be left open."""

    def __init__(self, start: str | pd.Timestamp | None = None,
                 end: str | pd.Timestamp | None = None) -> None:
        self.start = to_timestamp(start, "Start date") if start is not None else None
        self.end = to_timestamp(end, "End date") if end is not None else None
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValidationError("The end date is before the start date.")

    @classmethod
    def month(cls, month: str) -> DateRange:
        """One whole month, e.g. DateRange.month('2026-10')."""
        try:
            period = pd.Period(month, freq="M")
        except (ValueError, TypeError):
            raise ValidationError(f"{month!r} isn't a month. Use YYYY-MM.") from None
        return cls(period.start_time, period.end_time)

    def mask(self, sales: pd.DataFrame) -> pd.Series:
        keep = pd.Series(True, index=sales.index)
        if self.start is not None:
            keep &= sales["order_date"] >= self.start
        if self.end is not None:
            keep &= sales["order_date"] <= self.end
        return keep

    def describe(self) -> str:
        start = self.start.date().isoformat() if self.start is not None else "the start"
        end = self.end.date().isoformat() if self.end is not None else "the end"
        return f"{start} to {end}"


class IsOneOf(SalesFilter):
    """Rows where a column is one of some values, ignoring case. e.g. region is London."""

    def __init__(self, column: str, values: Iterable[str]) -> None:
        self.column = column
        self.values = [v.strip() for v in values if v.strip()]
        if not self.values:
            raise ValidationError(f"Give at least one {column} to filter by.")

    def mask(self, sales: pd.DataFrame) -> pd.Series:
        if self.column not in sales.columns:
            raise ValidationError(f"There's no {self.column!r} column to filter by.")
        wanted = {v.lower() for v in self.values}
        return sales[self.column].str.lower().isin(wanted)

    def describe(self) -> str:
        return f"{self.column} is {' or '.join(self.values)}"


class AllOf(SalesFilter):
    def __init__(self, *filters: SalesFilter) -> None:
        self.filters = filters

    def mask(self, sales: pd.DataFrame) -> pd.Series:
        keep = pd.Series(True, index=sales.index)
        for f in self.filters:
            keep &= f.mask(sales)
        return keep

    def describe(self) -> str:
        return " and ".join(f.describe() for f in self.filters)


class AnyOf(SalesFilter):
    def __init__(self, *filters: SalesFilter) -> None:
        self.filters = filters

    def mask(self, sales: pd.DataFrame) -> pd.Series:
        keep = pd.Series(False, index=sales.index)
        for f in self.filters:
            keep |= f.mask(sales)
        return keep

    def describe(self) -> str:
        return "(" + " or ".join(f.describe() for f in self.filters) + ")"


class Not(SalesFilter):
    def __init__(self, inner: SalesFilter) -> None:
        self.inner = inner

    def mask(self, sales: pd.DataFrame) -> pd.Series:
        return ~self.inner.mask(sales)

    def describe(self) -> str:
        return f"not {self.inner.describe()}"
