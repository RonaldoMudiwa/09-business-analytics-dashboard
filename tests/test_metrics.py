import pytest

from analytics import (
    DEFAULT_METRICS,
    AverageOrderValue,
    Customers,
    Metric,
    Orders,
    Profit,
    ProfitMargin,
    Revenue,
    UnitsSold,
    ValidationError,
    calculate_kpis,
    metric_named,
)

# The tiny shop in conftest: revenue £420.00, cost £230.00, 5 orders, 3 customers, 10 units.


@pytest.mark.parametrize("metric,expected", [
    (Revenue(), 42000),
    (Profit(), 42000 - 23000),
    (Orders(), 5),
    (Customers(), 3),
    (UnitsSold(), 10),
    (AverageOrderValue(), 42000 / 5),
])
def test_each_metric(sales, metric, expected):
    assert metric.compute(sales) == expected


def test_margin(sales):
    assert ProfitMargin().compute(sales) == pytest.approx(19000 / 42000)


@pytest.mark.parametrize("metric", DEFAULT_METRICS)
def test_every_metric_copes_with_no_sales(sales, metric):
    assert metric.compute(sales.iloc[0:0]) == 0


def test_formats(sales):
    texts = {k.name: k.text for k in calculate_kpis(sales)}
    assert texts == {"revenue": "£420.00", "profit": "£190.00", "margin": "45.2%",
                     "orders": "5", "aov": "£84.00", "customers": "3", "units": "10"}


def test_kpis_keep_the_order_given(sales):
    kpis = calculate_kpis(sales, [Orders(), Revenue()])
    assert [k.label for k in kpis] == ["Orders", "Revenue"]
    assert kpis[1].value == 42000


def test_a_new_metric_is_one_class(sales):
    class Products(Metric):
        name, label = "products", "Products sold"

        def compute(self, data):
            return data["product"].nunique()

    assert calculate_kpis(sales, [Products()])[0].text == "4"


def test_metric_named():
    assert isinstance(metric_named("profit"), Profit)
    with pytest.raises(ValidationError, match="Try one of: revenue, profit"):
        metric_named("sales")


def test_names_are_unique():
    names = [m.name for m in DEFAULT_METRICS]
    assert len(names) == len(set(names))
