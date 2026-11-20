import pandas as pd
import pytest

from analytics import DateRange, Everything, IsOneOf, SalesFilter, ValidationError


def ids(frame):
    return sorted(set(frame["order_id"]))


def test_everything(sales):
    assert isinstance(Everything(), SalesFilter)
    assert len(Everything().apply(sales)) == len(sales)
    assert Everything().describe() == "all sales"


def test_date_range_includes_both_ends(sales):
    assert ids(DateRange("2026-01-20", "2026-02-14").apply(sales)) == ["A2", "A3", "A4"]


def test_open_ended_ranges(sales):
    assert ids(DateRange(start="2026-02-14").apply(sales)) == ["A4", "A5"]
    assert ids(DateRange(end="2026-01-05").apply(sales)) == ["A1"]


def test_month(sales):
    february = DateRange.month("2026-02")
    assert ids(february.apply(sales)) == ["A3", "A4"]
    assert february.describe() == "2026-02-01 to 2026-02-28"


def test_describe_open_range():
    assert DateRange(start="2026-01-01").describe() == "2026-01-01 to the end"
    assert DateRange(end="2026-01-01").describe() == "the start to 2026-01-01"


def test_accepts_timestamps():
    assert DateRange(pd.Timestamp("2026-01-01 15:30")).start == pd.Timestamp("2026-01-01")


@pytest.mark.parametrize("start,end,message", [
    ("2026-02-01", "2026-01-01", "before the start"),
    ("tomorrow-ish", None, "isn't a date"),
])
def test_bad_date_ranges(start, end, message):
    with pytest.raises(ValidationError, match=message):
        DateRange(start, end)


def test_bad_month():
    with pytest.raises(ValidationError, match="isn't a month"):
        DateRange.month("Octember")


def test_is_one_of_ignores_case(sales):
    assert ids(IsOneOf("region", ["north"]).apply(sales)) == ["A2", "A4", "A5"]
    assert ids(IsOneOf("category", ["Camping", " clothing "]).apply(sales)) == ids(sales)


def test_is_one_of_needs_values():
    with pytest.raises(ValidationError, match="at least one region"):
        IsOneOf("region", ["  "])


def test_is_one_of_unknown_column(sales):
    with pytest.raises(ValidationError, match="no 'colour' column"):
        IsOneOf("colour", ["red"]).apply(sales)


def test_and_or_not(sales):
    north = IsOneOf("region", ["North"])
    online = IsOneOf("channel", ["Online"])
    assert ids((north & online).apply(sales)) == ["A5"]
    assert ids((north | online).apply(sales)) == ["A1", "A2", "A3", "A4", "A5"]
    assert ids((~north).apply(sales)) == ["A1", "A3"]


def test_combined_descriptions():
    north, store = IsOneOf("region", ["North"]), IsOneOf("channel", ["Store", "Online"])
    assert (north & store).describe() == "region is North and channel is Store or Online"
    assert (north | ~store).describe() == "(region is North or not channel is Store or Online)"
