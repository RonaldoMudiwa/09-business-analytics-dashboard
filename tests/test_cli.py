import io

import pytest

from analytics.cli import COMMANDS, build_parser, main

from .conftest import ROWS, make_frame


def run(*argv):
    out = io.StringIO()
    code = main(list(argv), out)
    return code, out.getvalue()


@pytest.fixture
def data(tmp_path):
    """The tiny shop as a CSV file."""
    path = tmp_path / "sales.csv"
    make_frame(ROWS).to_csv(path, index=False)
    return str(path)


def test_no_command_shows_help():
    code, out = run()
    assert code == 0
    assert "usage: python -m analytics" in out


def test_every_command_has_a_name_and_help():
    for command in COMMANDS:
        assert command.name and command.help
    assert "filters (work with every command)" in build_parser().format_help()


def test_summary(data):
    code, out = run("--data", data, "summary")
    assert code == 0
    assert "  Revenue                £420.00" in out
    assert "From 2026-01-05 to 2026-03-01" in out
    assert "Rows kept:                  6" in out


def test_filters_before_the_command(data):
    code, out = run("--data", data, "--region", "north", "--channel", "Store", "summary")
    assert out.startswith("Showing: region is north and channel is Store")
    assert "  Orders                       2" in out


def test_date_filters(data):
    code, out = run("--data", data, "--from", "2026-02-01", "--to", "2026-02-28", "summary")
    assert "Showing: 2026-02-01 to 2026-02-28" in out
    assert "  Revenue                 £60.00" in out


def test_more_than_one_value(data):
    code, out = run("--data", data, "--category", "Camping", "--category", "Clothing", "summary")
    assert "category is Camping or Clothing" in out


def test_nothing_matches(data):
    code, out = run("--data", data, "--region", "Wales", "summary")
    assert code == 1
    assert out == "Error: No sales match: region is Wales.\n"


def test_bad_date(data):
    code, out = run("--data", data, "--from", "soon", "summary")
    assert code == 1
    assert "isn't a date" in out


def test_missing_file(tmp_path):
    code, out = run("--data", str(tmp_path / "nope.csv"), "summary")
    assert code == 1
    assert "No file at" in out


def test_breakdown(data):
    code, out = run("--data", data, "breakdown", "--by", "region")
    lines = out.splitlines()
    assert lines[0].startswith("Region")
    assert lines[1].startswith("North") and "£270.00" in lines[1]
    assert lines[2].startswith("London")


def test_breakdown_top(data):
    code, out = run("--data", data, "breakdown", "--by", "product", "--top", "1", "--sort", "units")
    assert len(out.splitlines()) == 2
    assert out.splitlines()[1].startswith("Socks")


def test_breakdown_by_customer_heading(data):
    assert run("--data", data, "breakdown", "--by", "customer_id")[1].startswith("Customer id")


def test_compare(data):
    code, out = run("--data", data, "compare", "--month", "2026-02")
    assert out.startswith("2026-02-01 to 2026-02-28  vs  2026-01-01 to 2026-01-31")
    assert "£60.00       £160.00  ▼ -62.5%" in out


def test_compare_last_year(data):
    code, out = run("--data", data, "compare", "--vs", "last-year")
    assert "vs  2025-03-01 to 2025-03-31" in out
    assert "new" in out


def test_trend_with_short_history(data):
    code, out = run("--data", data, "trend", "--forecast", "2")
    assert code == 0
    assert "2026-01          £160.00" in out
    assert "2026-03          £200.00       £140.00" in out
    assert "Can't forecast: This forecast needs at least 12 months" in out


def test_trend_on_the_sample():
    code, out = run("trend")
    assert "Check: Same month last year, plus growth: off by 13.7%" in out


def test_customers(data):
    code, out = run("--data", data, "customers")
    assert out.startswith("Segment")
    assert "67% of customers came back for another order." in out


def test_dashboard_saves_html_and_excel(data, tmp_path):
    html, excel = tmp_path / "d.html", tmp_path / "d.xlsx"
    code, out = run("--data", data, "dashboard", "--title", "Tiny", "--html", str(html),
                    "--excel", str(excel))
    assert code == 0
    assert out.startswith("Tiny\n====")
    assert html.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert excel.exists()
    assert f"Saved {excel}." in out


def test_dashboard_without_saving(data, tmp_path):
    code, out = run("--data", data, "dashboard")
    assert code == 0
    assert "Saved" not in out


def test_demo():
    code, out = run("demo")
    assert code == 0
    assert "made up" in out
    assert "Outdoor shop sales" in out
    assert "  Revenue            £534,813.10" in out
