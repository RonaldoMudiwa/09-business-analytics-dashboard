import pytest
from openpyxl import load_workbook

from analytics import ExcelReport, build_dashboard
from analytics.excel import PERCENT, POUNDS


@pytest.fixture
def book(sales, tmp_path):
    path = ExcelReport().save(build_dashboard(sales, "Tiny shop"), tmp_path / "out" / "report.xlsx")
    return load_workbook(path)


def rows(sheet):
    return list(sheet.iter_rows(values_only=True))


def test_one_sheet_per_table(book):
    assert book.sheetnames == ["Summary", "Monthly", "Categories", "Regions", "Channels",
                               "Top products", "Customers"]


def test_summary(book):
    sheet = book["Summary"]
    assert sheet["A1"].value == "Tiny shop"
    assert rows(sheet)[3] == ("KPI", "All time", "2026-03", "Month before", "Change")
    assert sheet["A4"].font.b
    assert sheet.freeze_panes == "A5"
    revenue = rows(sheet)[4]
    assert revenue == ("Revenue", 420.0, 200.0, 60.0, "+233.3%")
    assert sheet["B5"].number_format == POUNDS


def test_counts_and_rates_keep_their_own_formats(book):
    sheet = book["Summary"]
    labels = [row[0] for row in rows(sheet)]
    margin_row = labels.index("Profit margin") + 1
    orders_row = labels.index("Orders") + 1
    assert sheet[f"B{margin_row}"].number_format == PERCENT
    assert sheet[f"E{margin_row}"].value.endswith(" pts")
    assert sheet[f"B{orders_row}"].value == 5


def test_notes_are_included(book):
    assert any(str(row[0]).startswith("Note: 2026-03 may not be finished") for row in rows(book["Summary"]))


def test_money_is_real_numbers_in_pounds(book):
    monthly = rows(book["Monthly"])
    assert monthly[0] == ("Month", "Revenue", "Profit", "3 month average", "Forecast")
    assert monthly[1] == ("2026-01", 160.0, 77.0, None, None)
    assert monthly[3][3] == pytest.approx(140.0)  # (160 + 60 + 200) / 3
    assert len(monthly) == 1 + 3 + 3  # heading, 3 months, 3 forecast months
    assert monthly[4][1] is None and monthly[4][4] is not None


def test_breakdown_sheet(book):
    categories = rows(book["Categories"])
    assert categories[1][:5] == ("Camping", 330.0, 135.0, 3, 4)
    assert book["Categories"]["F2"].number_format == PERCENT


def test_customers_sheet(book):
    customers = rows(book["Customers"])
    assert customers[0] == ("Segment", "Customers", "Revenue", "Share of revenue")
    assert customers[-1][0] == "Came back for another order"
    assert customers[-1][1] == pytest.approx(2 / 3)


def test_columns_are_wide_enough(book):
    assert book["Regions"].column_dimensions["A"].width >= 10


def test_adds_xlsx_if_missing(sales, tmp_path):
    path = ExcelReport().save(build_dashboard(sales), tmp_path / "report")
    assert path.name == "report.xlsx"
    assert [p.name for p in tmp_path.iterdir()] == ["report.xlsx"]


def test_cleans_up_after_a_failure(sales, tmp_path, monkeypatch):
    def broken_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("analytics.excel.os.replace", broken_replace)
    with pytest.raises(OSError):
        ExcelReport().save(build_dashboard(sales), tmp_path / "report.xlsx")
    assert list(tmp_path.iterdir()) == []
