"""Business Analytics Dashboard.

Reads a shop's sales, cleans them, and works out the numbers a manager
wants to see: totals, trends, best sellers and customers.

    from analytics import CsvSalesSource, SalesCleaner
"""

from .breakdowns import DIMENSIONS, SORT_KEYS, Breakdown, check_dimension, pivot
from .cleaning import (
    CleaningReport,
    CleanResult,
    SalesCleaner,
    add_money_columns,
    most_common_spelling,
)
from .comparison import Change, compare, latest_month, previous_period, same_period_last_year
from .customers import (
    DEFAULT_SEGMENTS,
    SegmentRule,
    add_segments,
    customer_table,
    repeat_rate,
    score,
    segment_summary,
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
from .trends import (
    Backtest,
    Forecaster,
    LinearTrend,
    SeasonalNaive,
    backtest,
    growth,
    monthly_series,
    rolling_average,
)

__version__ = "0.4.0"

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
    "Breakdown",
    "pivot",
    "check_dimension",
    "DIMENSIONS",
    "SORT_KEYS",
    "Change",
    "compare",
    "previous_period",
    "same_period_last_year",
    "latest_month",
    "monthly_series",
    "rolling_average",
    "growth",
    "Forecaster",
    "LinearTrend",
    "SeasonalNaive",
    "Backtest",
    "backtest",
    "customer_table",
    "add_segments",
    "segment_summary",
    "repeat_rate",
    "score",
    "SegmentRule",
    "DEFAULT_SEGMENTS",
    "to_pounds",
    "format_pounds",
    "format_percent",
    "AnalyticsError",
    "DataError",
    "ValidationError",
    "__version__",
]
