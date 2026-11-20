"""Business Analytics Dashboard.

Reads a shop's sales, cleans them, and works out the numbers a manager
wants to see: totals, trends, best sellers and customers.

    from analytics import CsvSalesSource, SalesCleaner
"""

from .cleaning import (
    CleaningReport,
    CleanResult,
    SalesCleaner,
    add_money_columns,
    most_common_spelling,
)
from .exceptions import AnalyticsError, DataError, ValidationError
from .filters import AllOf, AnyOf, DateRange, Everything, IsOneOf, Not, SalesFilter
from .metrics import (
    DEFAULT_METRICS,
    KPI,
    AverageOrderValue,
    Customers,
    Metric,
    MoneyMetric,
    Orders,
    Profit,
    ProfitMargin,
    Revenue,
    UnitsSold,
    calculate_kpis,
    metric_named,
)
from .money import format_percent, format_pounds, to_pounds
from .sources import REQUIRED_COLUMNS, CsvSalesSource, DataFrameSource, SalesSource

__version__ = "0.2.0"

__all__ = [
    "SalesSource",
    "CsvSalesSource",
    "DataFrameSource",
    "REQUIRED_COLUMNS",
    "SalesCleaner",
    "CleanResult",
    "CleaningReport",
    "add_money_columns",
    "most_common_spelling",
    "Metric",
    "MoneyMetric",
    "Revenue",
    "Profit",
    "ProfitMargin",
    "Orders",
    "AverageOrderValue",
    "Customers",
    "UnitsSold",
    "DEFAULT_METRICS",
    "KPI",
    "calculate_kpis",
    "metric_named",
    "SalesFilter",
    "Everything",
    "DateRange",
    "IsOneOf",
    "AllOf",
    "AnyOf",
    "Not",
    "to_pounds",
    "format_pounds",
    "format_percent",
    "AnalyticsError",
    "DataError",
    "ValidationError",
    "__version__",
]
