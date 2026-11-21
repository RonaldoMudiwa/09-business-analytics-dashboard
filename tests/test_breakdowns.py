import pytest

from analytics import Breakdown, ValidationError, pivot


def test_by_category(sales):
    table = Breakdown("category").table(sales)
    assert list(table.index) == ["Camping", "Clothing"]
    camping = table.loc["Camping"]
    assert camping["revenue"] == 33000
    assert camping["profit"] == 33000 - 19500
    assert camping["orders"] == 3
    assert camping["units"] == 4
    assert table["share"].sum() == pytest.approx(1)
    assert camping["margin"] == pytest.approx(13500 / 33000)


def test_months_stay_in_date_order(sales):
    table = Breakdown("month").table(sales)
    assert [str(m) for m in table.index] == ["2026-01", "2026-02", "2026-03"]
    assert list(table["revenue"]) == [16000, 6000, 20000]


def test_ties_are_sorted_by_name(sales):
    table = Breakdown("region").table(sales.assign(revenue_pence=100))
    assert list(table.index) == ["London", "North"]


def test_top(sales):
    top = Breakdown("product").top(sales, 2)
    assert list(top.index) == ["Tent", "Socks"]
    assert list(Breakdown("product").top(sales, 1, by="units").index) == ["Socks"]


def test_empty_sales(sales):
    table = Breakdown("region").table(sales.iloc[0:0])
    assert table.empty


def test_zero_revenue_has_zero_margin(sales):
    free = sales.assign(revenue_pence=0, profit_pence=0)
    table = Breakdown("region").table(free)
    assert list(table["margin"]) == [0.0, 0.0]
    assert list(table["share"]) == [0.0, 0.0]


@pytest.mark.parametrize("call,message", [
    (lambda s: Breakdown("colour"), "Can't break down by 'colour'"),
    (lambda s: Breakdown("region").top(s, 0), "at least 1"),
    (lambda s: Breakdown("region").top(s, 3, by="size"), "Can't sort by 'size'"),
])
def test_bad_requests(sales, call, message):
    with pytest.raises(ValidationError, match=message):
        call(sales)


def test_pivot(sales):
    grid = pivot(sales, "region", "category")
    assert list(grid.columns) == ["Camping", "Clothing", "Total"]
    assert grid.loc["London", "Camping"] == 13000
    assert grid.loc["London", "Clothing"] == 2000
    assert grid.loc["North", "Camping"] == 20000
    assert grid.loc["Total", "Total"] == 42000


def test_pivot_other_values(sales):
    assert pivot(sales, "channel", "region", "quantity").loc["Store", "North"] == 4


def test_pivot_needs_two_different_columns(sales):
    with pytest.raises(ValidationError, match="different"):
        pivot(sales, "region", "region")
    with pytest.raises(ValidationError):
        pivot(sales, "region", "colour")
