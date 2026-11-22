import pandas as pd
import pytest

from analytics import (
    DEFAULT_SEGMENTS,
    SegmentRule,
    ValidationError,
    add_segments,
    customer_table,
    repeat_rate,
    score,
    segment_summary,
)


def test_scores_split_into_thirds():
    assert list(score(pd.Series([10, 20, 30, 40, 50, 60]))) == [1, 1, 2, 2, 3, 3]


def test_lower_can_be_better():
    assert list(score(pd.Series([1, 100, 50]), higher_is_better=False)) == [3, 1, 2]


def test_same_value_same_score():
    assert list(score(pd.Series([5, 5, 5]))) == [2, 2, 2]


def test_one_customer():
    assert list(score(pd.Series([42]))) == [3]


def test_customer_table(sales):
    table = customer_table(sales)
    c1 = table.loc["C1"]
    assert c1["orders"] == 2
    assert c1["revenue"] == 10000 + 2000 + 3000
    assert c1["first_order"] == pd.Timestamp("2026-01-05")
    # The last sale is 1 March, so "today" is 2 March.
    assert c1["recency_days"] == (pd.Timestamp("2026-03-02") - pd.Timestamp("2026-02-03")).days
    assert table.loc["C2", "recency_days"] == 1
    assert table.loc["C2", "r"] == 3


def test_customer_table_as_of(sales):
    table = customer_table(sales, as_of="2026-03-31")
    assert table.loc["C2", "recency_days"] == 30


def test_as_of_before_the_sales(sales):
    with pytest.raises(ValidationError, match="before some of the sales"):
        customer_table(sales, as_of="2026-01-01")


def test_no_sales(sales):
    with pytest.raises(ValidationError):
        customer_table(sales.iloc[0:0])


def table_of(r, f, m):
    return pd.DataFrame({"r": [r], "f": [f], "m": [m], "orders": [1], "revenue": [100]},
                        index=["C1"])


@pytest.mark.parametrize("r,f,expected", [
    (3, 3, "Champions"), (2, 3, "Loyal"), (3, 1, "New or returning"), (1, 2, "At risk"),
    (1, 1, "Lost"), (2, 2, "Steady"),
])
def test_segments(r, f, expected):
    assert add_segments(table_of(r, f, 2)).loc["C1", "segment"] == expected


def test_no_rule_fits():
    rules = [SegmentRule("Big spenders", "Spend the most", lambda r, f, m: m == 3)]
    assert add_segments(table_of(1, 1, 1), rules).loc["C1", "segment"] == "Other"


def test_segment_summary(sales):
    summary = segment_summary(customer_table(sales))
    assert summary["customers"].sum() == 3
    assert summary["revenue"].sum() == 42000
    assert summary["share_of_revenue"].sum() == pytest.approx(1)
    rule_order = [r.name for r in DEFAULT_SEGMENTS]
    positions = [rule_order.index(name) for name in summary.index]
    assert positions == sorted(positions)


def test_repeat_rate(sales):
    # C1 and C2 came back, C3 bought once.
    assert repeat_rate(sales) == pytest.approx(2 / 3)
    assert repeat_rate(sales.iloc[0:0]) == 0.0


def test_segment_summary_uses_segments_already_there(sales):
    table = add_segments(customer_table(sales)).assign(segment="Champions")
    assert list(segment_summary(table).index) == ["Champions"]
