"""Things many tests share."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from analytics import DataFrameSource, SalesCleaner

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_sales.csv"

# A tiny shop with numbers that are easy to check by hand.
# order, date, customer, region, channel, category, product, qty, price, cost
ROWS = [
    ("A1", "2026-01-05", "C1", "London", "Online", "Camping", "Tent", 1, 10000, 6000),
    ("A1", "2026-01-05", "C1", "London", "Online", "Clothing", "Socks", 2, 1000, 400),
    ("A2", "2026-01-20", "C2", "North", "Store", "Clothing", "Fleece", 1, 4000, 1500),
    ("A3", "2026-02-03", "C1", "London", "Online", "Camping", "Stove", 1, 3000, 1500),
    ("A4", "2026-02-14", "C3", "North", "Store", "Clothing", "Socks", 3, 1000, 400),
    ("A5", "2026-03-01", "C2", "North", "Online", "Camping", "Tent", 2, 10000, 6000),
]


def make_frame(rows=ROWS) -> pd.DataFrame:
    columns = ["order_id", "order_date", "customer_id", "region", "channel", "category",
               "product", "quantity", "unit_price_pence", "unit_cost_pence"]
    return pd.DataFrame([[str(v) for v in row] for row in rows], columns=columns)


@pytest.fixture
def raw() -> pd.DataFrame:
    return make_frame()


@pytest.fixture
def sales() -> pd.DataFrame:
    """The tiny shop, cleaned."""
    return SalesCleaner().clean(DataFrameSource(make_frame()).load()).frame
