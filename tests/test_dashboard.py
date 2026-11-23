import pandas as pd
import pytest

from analytics import (
    CsvSalesSource,
    DashboardRenderer,
    HtmlDashboard,
    IsOneOf,
    LinearTrend,
    SalesCleaner,
    SeasonalNaive,
    TextDashboard,
    ValidationError,
    build_dashboard,
    monthly_series,
    pick_forecaster,
)
from analytics.dashboard import bar, write_safely

from .conftest import ROWS, SAMPLE, make_frame


@pytest.fixture(scope="module")
def big_sales():
    return SalesCleaner().clean(CsvSalesSource(SAMPLE).load()).frame


def test_build_dashboard(sales):
    board = build_dashboard(sales, "Tiny shop")
    assert board.title == "Tiny shop"
    assert board.showing == "all sales"
    assert board.latest_month == "2026-03"
    assert {k.name: k.value for k in board.kpis}["revenue"] == 42000
    assert list(board.monthly.columns) == ["revenue", "average", "profit"]
    assert len(board.forecast) == 3
    assert board.forecast_check is None  # too little history to check a forecast
    assert list(board.categories.index) == ["Camping", "Clothing"]
    assert board.segments["customers"].sum() == 3


def test_filtered_dashboard(sales):
    board = build_dashboard(sales, where=IsOneOf("region", ["North"]))
    assert board.showing == "region is North"
    assert list(board.regions.index) == ["North"]


def test_nothing_matches(sales):
    with pytest.raises(ValidationError, match="No sales match: region is Wales"):
        build_dashboard(sales, where=IsOneOf("region", ["Wales"]))


def test_note_when_the_last_month_is_not_over(sales):
    assert "2026-03 may not be finished yet" in build_dashboard(sales).notes[0]


def test_no_note_when_the_month_is_over():
    rows = ROWS + [("A6", "2026-03-31", "C1", "London", "Online", "Camping", "Tent", 1, 100, 50)]
    sales = SalesCleaner().clean(make_frame(rows)).frame
    assert build_dashboard(sales).notes == []


def test_pick_forecaster_uses_the_more_accurate_one(big_sales):
    forecaster, check = pick_forecaster(monthly_series(big_sales))
    assert isinstance(forecaster, SeasonalNaive)
    assert check.name == SeasonalNaive.name


def test_pick_forecaster_short_history():
    history = pd.Series([1.0] * 5, index=pd.period_range("2026-01", periods=5, freq="M"))
    forecaster, check = pick_forecaster(history)
    assert isinstance(forecaster, LinearTrend) and check is None


def test_bar():
    assert bar(50, 100, 10) == "█████"
    assert bar(5, 0) == ""


def test_text_dashboard(sales):
    text = TextDashboard().render(build_dashboard(sales, "Tiny shop"))
    assert isinstance(TextDashboard(), DashboardRenderer)
    assert text.startswith("Tiny shop\n=========\n2026-01-05 to 2026-03-01  (all sales)")
    assert "  Revenue                £420.00" in text
    assert "2026-03 compared with the month before:" in text
    assert "forecast" in text
    assert "  Camping" in text
    assert "came back for another order" in text
    assert "Note: 2026-03 may not be finished yet" in text


def test_text_dashboard_on_the_sample(big_sales):
    text = TextDashboard().render(build_dashboard(big_sales))
    assert "  Revenue            £534,813.10" in text
    assert "(Forecast: Same month last year, plus growth" in text
    assert "     110 customers" in text


def test_html_dashboard(sales, tmp_path):
    board = build_dashboard(sales, "Tiny <shop> & co")
    page = HtmlDashboard().render(board)
    assert page.startswith("<!DOCTYPE html>")
    assert "<title>Tiny &lt;shop&gt; &amp; co</title>" in page
    assert "Tiny <shop>" not in page
    assert page.count("data:image/png;base64,") == 5
    assert "£420.00" in page
    assert "vs month before" in page


def test_html_escapes_names_from_the_data():
    rows = [ROWS[0][:6] + ("<script>alert(1)</script>",) + ROWS[0][7:]] + ROWS[1:]
    page = HtmlDashboard().render(build_dashboard(SalesCleaner().clean(make_frame(rows)).frame))
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_save(sales, tmp_path):
    path = HtmlDashboard().save(build_dashboard(sales), tmp_path / "out" / "dash.html")
    assert path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert [p.name for p in path.parent.iterdir()] == ["dash.html"]


def test_write_safely_cleans_up_after_a_failure(tmp_path, monkeypatch):
    def broken_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("analytics.dashboard.os.replace", broken_replace)
    with pytest.raises(OSError):
        write_safely(tmp_path / "a.txt", "hello")
    assert list(tmp_path.iterdir()) == []
