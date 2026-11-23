import base64

import pandas as pd
import pytest

from analytics import BarChart, Chart, TrendChart
from analytics.charts import pounds_axis

PNG_START = b"\x89PNG"


def months(values, start="2026-01"):
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"),
                     dtype="float64")


@pytest.mark.parametrize("pence,text", [(2_500_000, "£25k"), (50_000, "£500"), (0, "£0")])
def test_pounds_axis(pence, text):
    assert pounds_axis(pence, 0) == text


def test_trend_chart_makes_a_png():
    revenue = months([100, 200, 300, 250])
    chart = TrendChart("Revenue", revenue, revenue.rolling(3).mean(), months([260], "2026-05"))
    assert isinstance(chart, Chart)
    assert chart.to_png().startswith(PNG_START)


def test_trend_chart_without_a_forecast():
    revenue = months([100, 200])
    ax = TrendChart("Revenue", revenue, revenue).figure().axes[0]
    assert sorted(t.get_text() for t in ax.get_legend().get_texts()) == ["3 month average",
                                                                        "Revenue"]


def test_trend_chart_draws_every_bar():
    revenue = months([100, 200, 300])
    ax = TrendChart("Revenue", revenue, revenue, months([1, 2], "2026-04")).figure().axes[0]
    assert len(ax.patches) == 5
    assert ax.get_title(loc="left") == "Revenue"


def test_bar_chart_biggest_at_the_top():
    values = pd.Series([300, 100], index=["Camping", "Clothing"])
    ax = BarChart("Categories", values).figure().axes[0]
    labels = [t.get_text() for t in ax.get_yticklabels()]
    assert labels == ["Clothing", "Camping"]  # matplotlib lists them bottom up


def bar_labels(chart):
    return [t.get_text() for t in chart.figure().axes[0].texts]


def test_bar_chart_labels_money_in_pounds():
    assert bar_labels(BarChart("Revenue", pd.Series([2_500_000], index=["Online"]))) == ["£25k"]


def test_bar_chart_counts_instead_of_money():
    assert bar_labels(BarChart("Orders", pd.Series([1200], index=["Online"]), money=False)) == \
        ["1,200"]


def test_bar_chart_gets_taller_with_more_bars():
    few = BarChart("A", pd.Series([1], index=["x"]))
    many = BarChart("B", pd.Series(range(10), index=list("abcdefghij")))
    assert many.height > few.height


def test_data_uri():
    revenue = months([100])
    uri = TrendChart("Revenue", revenue, revenue).to_data_uri()
    assert uri.startswith("data:image/png;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]).startswith(PNG_START)
