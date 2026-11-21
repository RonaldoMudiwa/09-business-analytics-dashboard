import pandas as pd
import pytest

from analytics import (
    Change,
    DateRange,
    Orders,
    ProfitMargin,
    Revenue,
    ValidationError,
    compare,
    latest_month,
    previous_period,
    same_period_last_year,
)


def dates(period):
    return period.start.date().isoformat(), period.end.date().isoformat()


def test_previous_month():
    assert dates(previous_period(DateRange.month("2026-03"))) == ("2026-02-01", "2026-02-28")


def test_previous_month_across_a_new_year():
    assert dates(previous_period(DateRange.month("2026-01"))) == ("2025-12-01", "2025-12-31")


def test_previous_quarter():
    quarter = DateRange("2026-04-01", "2026-06-30")
    assert dates(previous_period(quarter)) == ("2026-01-01", "2026-03-31")


def test_previous_days():
    week = DateRange("2026-03-09", "2026-03-15")
    assert dates(previous_period(week)) == ("2026-03-02", "2026-03-08")


def test_same_period_last_year():
    assert dates(same_period_last_year(DateRange.month("2026-10"))) == ("2025-10-01", "2025-10-31")


def test_leap_day():
    assert dates(same_period_last_year(DateRange("2028-02-29", "2028-02-29"))) == \
        ("2027-02-28", "2027-02-28")


def test_open_ranges_cannot_be_compared():
    with pytest.raises(ValidationError, match="start and an end"):
        previous_period(DateRange(start="2026-01-01"))


def test_compare_two_months(sales):
    changes = compare(sales, DateRange.month("2026-02"), DateRange.month("2026-01"),
                      [Revenue(), Orders()])
    revenue, orders = changes
    assert (revenue.current, revenue.previous) == (6000, 16000)
    assert revenue.difference == -10000
    assert revenue.percent == pytest.approx(-0.625)
    assert revenue.arrow() == "▼"
    assert revenue.percent_text() == "-62.5%"
    assert (revenue.current_text, revenue.previous_text) == ("£60.00", "£160.00")
    assert orders.arrow() == "▬"
    assert orders.percent_text() == "0.0%"


def test_going_up():
    change = Change("Revenue", 150, 100, "", "")
    assert change.arrow() == "▲"
    assert change.percent_text() == "+50.0%"


def test_nothing_before_is_new():
    change = Change("Revenue", 500, 0, "£5.00", "£0.00")
    assert change.percent is None
    assert change.percent_text() == "new"


def test_rates_show_points(sales):
    margin = compare(sales, DateRange.month("2026-02"), DateRange.month("2026-01"),
                     [ProfitMargin()])[0]
    assert margin.is_rate
    # January 7,700 / 16,000 = 48.1%, February 3,300 / 6,000 = 55.0%
    assert margin.percent_text() == "+6.9 pts"


def test_latest_month(sales):
    assert latest_month(sales) == "2026-03"


def test_latest_month_needs_sales(sales):
    with pytest.raises(ValidationError):
        latest_month(sales.iloc[0:0])
