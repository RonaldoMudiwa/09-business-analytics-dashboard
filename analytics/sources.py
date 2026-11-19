"""Where the sales data comes from.

SalesSource is the base class. Today there's a CSV file and a ready made
DataFrame. A database or a web API could be added later as another class,
and nothing that uses the data would need to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from .exceptions import DataError

# Every sales file must have these columns. Prices are in whole pennies.
REQUIRED_COLUMNS = (
    "order_id", "order_date", "customer_id", "region", "channel", "category",
    "product", "quantity", "unit_price_pence", "unit_cost_pence",
)


def check_columns(frame: pd.DataFrame, where: str) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise DataError(f"{where} is missing these columns: {', '.join(missing)}.")


class SalesSource(ABC):
    """Gives back the raw sales rows as a DataFrame, before any cleaning."""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Every row, with at least the REQUIRED_COLUMNS."""


class CsvSalesSource(SalesSource):
    """Reads a CSV file, e.g. an export from a till or online shop."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        if not self.path.is_file():
            raise DataError(f"No file at {self.path}.")
        try:
            # Read everything as text first. The cleaner decides what's a valid number or date.
            frame = pd.read_csv(self.path, dtype=str, keep_default_na=False,
                                encoding="utf-8-sig")
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
            raise DataError(f"{self.path.name} couldn't be read as a CSV file: {error}") from None
        frame.columns = [c.strip().lower() for c in frame.columns]
        check_columns(frame, self.path.name)
        return frame


class DataFrameSource(SalesSource):
    """Data that's already in a DataFrame. Handy for tests."""

    def __init__(self, frame: pd.DataFrame) -> None:
        check_columns(frame, "The data")
        self._frame = frame

    def load(self) -> pd.DataFrame:
        # A copy, so whoever uses it can't change ours by accident.
        return self._frame.copy()
