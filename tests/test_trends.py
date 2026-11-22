import numpy as np
import pandas as pd
import pytest

from analytics import (
    CsvSalesSource,
    Forecaster,
    LinearTrend,
    SalesCleaner,
    SeasonalNaive,
    ValidationError,
    backtest,
    growth,
    monthly_series,
    rolling_average,
)

from .conftest import SAMPLE


def series(values, start="2025-01"):
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"),
                     dtype="float64")


def test_monthly_series(sales):
    revenue = monthly_series(sales)
    assert [str(m) for m in revenue.index] == ["2026-01", "2026-02", "2026-03"]
    assert list(revenue) == [16000, 6000, 20000]
    assert list(monthly_series(sales, "quantity")) == [4, 4, 2]


def test_months_with_no_sales_are_zero(sales):
    without_february = sales[sales["month"] != pd.Period("2026-02", "M")]
    assert list(monthly_series(without_february)) == [16000, 0, 20000]


def test_monthly_series_of_nothing(sales):
    assert monthly_series(sales.iloc[0:0]).empty


def test_monthly_series_bad_column(sales):
    with pytest.raises(ValidationError, match="Can't track"):
        monthly_series(sales, "colour")


def test_rolling_average():
    smooth = rolling_average(series([3, 6, 9, 12]), window=3)
    assert np.isnan(smooth.iloc[0]) and np.isnan(smooth.iloc[1])
    assert list(smooth.iloc[2:]) == [6, 9]


def test_rolling_average_bad_window():
    with pytest.raises(ValidationError):
        rolling_average(series([1]), 0)


def test_growth():
    changes = growth(series([100, 110, 0, 50]))
    assert np.isnan(changes.iloc[0])
    assert changes.iloc[1] == pytest.approx(0.1)
    assert changes.iloc[2] == -1
    assert np.isnan(changes.iloc[3])  # can't grow from 0 by a percentage


def test_linear_trend_carries_a_straight_line_on():
    forecast = LinearTrend().predict(series([10, 20, 30, 40]), 2)
    assert isinstance(LinearTrend(), Forecaster)
    assert [str(m) for m in forecast.index] == ["2025-05", "2025-06"]
    assert list(forecast.round(6)) == [50, 60]


def test_linear_trend_never_goes_below_zero():
    assert list(LinearTrend().predict(series([30, 20, 10]), 3)) == [0, 0, 0]


def test_linear_trend_with_one_month():
    assert list(LinearTrend().predict(series([7]), 2)) == [7, 7]


def test_seasonal_naive_copies_last_year():
    history = series(range(1, 13))
    forecast = SeasonalNaive().predict(history, 2)
    assert list(forecast) == [1, 2]


def test_seasonal_naive_adds_growth():
    # The second year is double the first, so next year should double again.
    history = series(list(range(1, 13)) + [2 * n for n in range(1, 13)])
    assert list(SeasonalNaive().predict(history, 2)) == [4, 8]


def test_seasonal_naive_more_than_a_year_ahead():
    forecast = SeasonalNaive().predict(series([5] * 12), 14)
    assert len(forecast) == 14
    assert forecast.iloc[-1] == 5


def test_seasonal_naive_needs_a_year():
    with pytest.raises(ValidationError, match="12 months"):
        SeasonalNaive().predict(series([1] * 11), 1)


def test_seasonal_naive_growth_from_nothing():
    history = series([0] * 12 + [5] * 12)
    assert list(SeasonalNaive().predict(history, 1)) == [5]


@pytest.mark.parametrize("months,history,message", [
    (0, [1, 2], "at least 1"),
    (1, [], "needs some history"),
])
def test_bad_forecasts(months, history, message):
    with pytest.raises(ValidationError, match=message):
        LinearTrend().predict(series(history), months)


def test_backtest_a_perfect_forecast():
    result = backtest(LinearTrend(), series([10, 20, 30, 40, 50]), holdout=2)
    assert result.average_error == pytest.approx(0)
    assert result.text() == "Straight line trend: off by 0.0% on average over 2 months"


def test_backtest_measures_how_far_off():
    # Flat at 100, then 200 and 50 really happen: off by 50% and 100%.
    result = backtest(LinearTrend(), series([100, 100, 100, 200, 50]), holdout=2)
    assert result.average_error == pytest.approx(0.75)


def test_backtest_skips_months_that_were_zero():
    result = backtest(LinearTrend(), series([100, 100, 0, 50]), holdout=2)
    assert result.average_error == pytest.approx(1.0)


@pytest.mark.parametrize("holdout", [0, 5])
def test_bad_holdout(holdout):
    with pytest.raises(ValidationError):
        backtest(LinearTrend(), series([1, 2, 3, 4, 5]), holdout)


def test_on_the_sample_the_seasonal_forecast_wins():
    sales = SalesCleaner().clean(CsvSalesSource(SAMPLE).load()).frame
    history = monthly_series(sales)
    straight = backtest(LinearTrend(), history, 6)
    seasonal = backtest(SeasonalNaive(), history, 6)
    assert seasonal.average_error < straight.average_error
