"""Breaking the totals down: by month, category, region, channel or product.

A total says "we took £500k". A breakdown says where it came from:
which months were busy, which products sell, which regions buy most.
This is pandas' groupby: put the rows into piles by one column, then add
each pile up. Like sorting receipts into envelopes, one per month, and
totalling each envelope.
"""

from __future__ import annotations

import pandas as pd

from .exceptions import ValidationError

# The columns it makes sense to group by.
DIMENSIONS = ("month", "category", "region", "channel", "product", "customer_id")
# What a breakdown table can be sorted by.
SORT_KEYS = ("revenue", "profit", "orders", "units")


def check_dimension(name: str) -> str:
    if name not in DIMENSIONS:
        raise ValidationError(f"Can't break down by {name!r}. Try one of: {', '.join(DIMENSIONS)}.")
    return name


class Breakdown:
    """Totals for each value of one column, e.g. each region."""

    def __init__(self, by: str) -> None:
        self.by = check_dimension(by)

    def table(self, sales: pd.DataFrame) -> pd.DataFrame:
        """One row per group, with revenue, profit, orders, units, share and margin.

        Months are kept in date order. Everything else is biggest revenue first.
        """
        grouped = sales.groupby(self.by, observed=True).agg(
            revenue=("revenue_pence", "sum"),
            profit=("profit_pence", "sum"),
            orders=("order_id", "nunique"),
            units=("quantity", "sum"),
        )
        total = grouped["revenue"].sum()
        grouped["share"] = grouped["revenue"] / total if total else 0.0
        grouped["margin"] = (grouped["profit"] / grouped["revenue"].where(grouped["revenue"] != 0)
                             ).fillna(0.0)
        if self.by == "month":
            return grouped.sort_index()
        # Ties are broken by name, so the order never jumps around.
        return grouped.reset_index().sort_values(
            ["revenue", self.by], ascending=[False, True]).set_index(self.by)

    def top(self, sales: pd.DataFrame, n: int = 5, by: str = "revenue") -> pd.DataFrame:
        """The n best groups, by revenue, profit, orders or units."""
        if n < 1:
            raise ValidationError("n must be at least 1.")
        if by not in SORT_KEYS:
            raise ValidationError(f"Can't sort by {by!r}. Try one of: {', '.join(SORT_KEYS)}.")
        table = self.table(sales).reset_index()
        return table.sort_values([by, self.by], ascending=[False, True]).head(n).set_index(self.by)


def pivot(sales: pd.DataFrame, rows: str, columns: str,
          value: str = "revenue_pence") -> pd.DataFrame:
    """A grid, like a spreadsheet pivot table: e.g. regions down the side, categories across.

    Gaps are 0, and a Total row and column are added.
    """
    check_dimension(rows)
    check_dimension(columns)
    if rows == columns:
        raise ValidationError("Rows and columns must be different.")
    grid = sales.pivot_table(index=rows, columns=columns, values=value, aggfunc="sum",
                             fill_value=0, margins=True, margins_name="Total", observed=True)
    grid.columns.name = None
    return grid.astype("int64")
