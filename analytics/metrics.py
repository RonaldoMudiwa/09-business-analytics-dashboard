"""KPIs: the handful of numbers a manager checks first.

KPI stands for key performance indicator. Revenue, profit, how many orders,
how much people spend per order. Each one is its own small Metric class
with one job: work out its number from the sales, and show it nicely.
Adding a new KPI means adding one class, nothing else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from .exceptions import ValidationError
from .money import format_percent, format_pounds


class Metric(ABC):
    """One KPI. name is a short key like 'revenue', label is what people see."""

    name = ""
    label = ""
    # True for numbers that are already a percentage, like the margin.
    is_rate = False

    @abstractmethod
    def compute(self, sales: pd.DataFrame) -> float:
        """Work out the number from clean sales rows. Must cope with no rows."""

    def format(self, value: float) -> str:
        """How the number is shown. Plain whole numbers unless a subclass says otherwise."""
        return f"{value:,.0f}"


class MoneyMetric(Metric, ABC):
    """A metric measured in pennies, shown in pounds."""

    def format(self, value: float) -> str:
        return format_pounds(value)


class Revenue(MoneyMetric):
    name, label = "revenue", "Revenue"

    def compute(self, sales: pd.DataFrame) -> float:
        return int(sales["revenue_pence"].sum())


class Profit(MoneyMetric):
    name, label = "profit", "Gross profit"

    def compute(self, sales: pd.DataFrame) -> float:
        return int(sales["profit_pence"].sum())


class ProfitMargin(Metric):
    """How much of each pound taken is profit. 0.5 means 50p in every £1."""

    name, label = "margin", "Profit margin"
    is_rate = True

    def compute(self, sales: pd.DataFrame) -> float:
        revenue = sales["revenue_pence"].sum()
        return float(sales["profit_pence"].sum() / revenue) if revenue else 0.0

    def format(self, value: float) -> str:
        return format_percent(value)


class Orders(Metric):
    """One order can have several rows (one per product), so we count order ids."""

    name, label = "orders", "Orders"

    def compute(self, sales: pd.DataFrame) -> float:
        return int(sales["order_id"].nunique())


class AverageOrderValue(MoneyMetric):
    """What a customer spends in one go, on average."""

    name, label = "aov", "Average order"

    def compute(self, sales: pd.DataFrame) -> float:
        orders = sales["order_id"].nunique()
        return float(sales["revenue_pence"].sum() / orders) if orders else 0.0


class Customers(Metric):
    name, label = "customers", "Customers"

    def compute(self, sales: pd.DataFrame) -> float:
        return int(sales["customer_id"].nunique())


class UnitsSold(Metric):
    name, label = "units", "Units sold"

    def compute(self, sales: pd.DataFrame) -> float:
        return int(sales["quantity"].sum())


DEFAULT_METRICS: tuple[Metric, ...] = (
    Revenue(), Profit(), ProfitMargin(), Orders(), AverageOrderValue(), Customers(), UnitsSold(),
)


@dataclass(frozen=True)
class KPI:
    """One worked out KPI, ready to show."""

    name: str
    label: str
    value: float
    text: str


def calculate_kpis(sales: pd.DataFrame,
                   metrics: Sequence[Metric] = DEFAULT_METRICS) -> list[KPI]:
    """Every metric's KPI, in the order given."""
    kpis = []
    for metric in metrics:
        value = metric.compute(sales)
        kpis.append(KPI(metric.name, metric.label, value, metric.format(value)))
    return kpis


def metric_named(name: str, metrics: Sequence[Metric] = DEFAULT_METRICS) -> Metric:
    for metric in metrics:
        if metric.name == name:
            return metric
    raise ValidationError(f"No metric called {name!r}. "
                          f"Try one of: {', '.join(m.name for m in metrics)}.")
