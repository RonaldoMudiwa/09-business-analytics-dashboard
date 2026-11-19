"""Business Analytics Dashboard.

Reads a shop's sales, cleans them, and works out the numbers a manager
wants to see: totals, trends, best sellers and customers.

    from analytics import CsvSalesSource, SalesCleaner
"""

from .cleaning import CleaningReport, CleanResult, SalesCleaner, add_money_columns, most_common_spelling
from .exceptions import AnalyticsError, DataError, ValidationError
from .money import format_percent, format_pounds, to_pounds
from .sources import REQUIRED_COLUMNS, CsvSalesSource, DataFrameSource, SalesSource

__version__ = "0.1.0"

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
    "to_pounds",
    "format_pounds",
    "format_percent",
    "AnalyticsError",
    "DataError",
    "ValidationError",
    "__version__",
]
