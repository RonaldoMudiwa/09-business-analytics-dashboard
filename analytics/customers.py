"""Who the customers are: RFM scores and segments.

RFM looks at three things for each customer:

- Recency:   how long since they last bought. Recent is good.
- Frequency: how many orders they've made. More is good.
- Monetary:  how much they've spent in total. More is good.

Each gets a score from 1 (bottom third of customers) to 3 (top third).
Then simple rules put each customer in a group, like a gym sorting
members into "comes every week", "used to come" and "just joined", so
each group can get the right message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
import pandas as pd

from .exceptions import ValidationError

Scores = Callable[[int, int, int], bool]


@dataclass(frozen=True)
class SegmentRule:
    """A named group of customers. test gets the R, F and M scores."""

    name: str
    meaning: str
    test: Scores


# Checked from the top. The first rule that fits wins.
DEFAULT_SEGMENTS: tuple[SegmentRule, ...] = (
    SegmentRule("Champions", "Bought recently, buy often and spend the most",
                lambda r, f, m: r == 3 and f == 3),
    SegmentRule("Loyal", "Buy often", lambda r, f, m: f == 3),
    SegmentRule("New or returning", "Bought recently, but not often yet",
                lambda r, f, m: r == 3 and f == 1),
    SegmentRule("At risk", "Used to buy often but haven't for a while",
                lambda r, f, m: r == 1 and f >= 2),
    SegmentRule("Lost", "One or two orders, a long time ago", lambda r, f, m: r == 1),
    SegmentRule("Steady", "Somewhere in the middle", lambda r, f, m: True),
)


def score(values: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Split customers into thirds: 1 for the bottom third, 3 for the top.

    Customers with the same value always get the same score.
    """
    ranks = values.rank(method="average", pct=True, ascending=higher_is_better)
    return np.ceil(ranks * 3).clip(1, 3).astype("int64")


def customer_table(sales: pd.DataFrame, as_of: str | pd.Timestamp | None = None) -> pd.DataFrame:
    """One row per customer with their totals and R, F and M scores.

    as_of is "today" for working out recency. It defaults to the day after
    the last sale, so the newest customer has a recency of 1 day.
    """
    if sales.empty:
        raise ValidationError("There are no sales to look at customers in.")
    today = (pd.Timestamp(as_of).normalize() if as_of is not None
             else sales["order_date"].max() + pd.Timedelta(days=1))
    table = sales.groupby("customer_id").agg(
        first_order=("order_date", "min"),
        last_order=("order_date", "max"),
        orders=("order_id", "nunique"),
        revenue=("revenue_pence", "sum"),
    )
    table["recency_days"] = (today - table["last_order"]).dt.days
    if (table["recency_days"] < 0).any():
        raise ValidationError("as_of is before some of the sales.")
    table["r"] = score(table["recency_days"], higher_is_better=False)
    table["f"] = score(table["orders"])
    table["m"] = score(table["revenue"])
    return table


def add_segments(table: pd.DataFrame,
                 rules: Sequence[SegmentRule] = DEFAULT_SEGMENTS) -> pd.DataFrame:
    """Adds a 'segment' column using the first rule that fits each customer."""
    def pick(row: pd.Series) -> str:
        for rule in rules:
            if rule.test(row["r"], row["f"], row["m"]):
                return rule.name
        return "Other"

    return table.assign(segment=table.apply(pick, axis=1))


def segment_summary(table: pd.DataFrame,
                    rules: Sequence[SegmentRule] = DEFAULT_SEGMENTS) -> pd.DataFrame:
    """How many customers are in each segment, and how much they spend. In the rules' order."""
    if "segment" not in table.columns:
        table = add_segments(table, rules)
    summary = table.groupby("segment").agg(customers=("orders", "size"),
                                           revenue=("revenue", "sum"))
    summary["share_of_revenue"] = summary["revenue"] / summary["revenue"].sum()
    order = [r.name for r in rules] + ["Other"]
    return summary.reindex([name for name in order if name in summary.index])


def repeat_rate(sales: pd.DataFrame) -> float:
    """The share of customers who came back for a second order."""
    orders = sales.groupby("customer_id")["order_id"].nunique()
    return float((orders > 1).mean()) if len(orders) else 0.0
