import pandas as pd
import pytest

from analytics import CsvSalesSource, SalesCleaner, most_common_spelling

from .conftest import ROWS, SAMPLE, make_frame


def clean(rows):
    return SalesCleaner().clean(make_frame(rows))


def test_clean_rows_are_kept_and_typed(sales):
    assert len(sales) == 6
    assert sales["quantity"].dtype == "int64"
    assert pd.api.types.is_datetime64_any_dtype(sales["order_date"])
    assert str(sales.loc[0, "month"]) == "2026-01"


def test_money_columns_are_worked_out(sales):
    socks = sales[sales["order_id"] == "A1"].iloc[1]
    assert socks["revenue_pence"] == 2000
    assert socks["cost_pence"] == 800
    assert socks["profit_pence"] == 1200
    assert sales["revenue_pence"].sum() == 10000 + 2000 + 4000 + 3000 + 3000 + 20000


def test_exact_copies_are_removed():
    result = clean(ROWS + [ROWS[0], ROWS[0]])
    assert result.report.duplicates == 2
    assert len(result.frame) == 6


def test_missing_values_are_dropped():
    row = list(ROWS[0])
    row[2] = " "
    result = clean([tuple(row)] + ROWS[1:])
    assert result.report.missing_values == 1
    assert len(result.frame) == 5


def test_bad_dates_are_dropped():
    rows = [ROWS[0][:1] + ("not a date",) + ROWS[0][2:],
            ROWS[1][:1] + ("05/01/2026",) + ROWS[1][2:]] + ROWS[2:]
    result = clean(rows)
    assert result.report.bad_dates == 2
    assert len(result.frame) == 4


@pytest.mark.parametrize("column,value", [(7, "-1"), (7, "0"), (7, "two"), (7, "1.5"),
                                          (8, "-5"), (9, "x")])
def test_bad_numbers_are_dropped(column, value):
    row = list(ROWS[0])
    row[column] = value
    result = clean([tuple(row)] + ROWS[1:])
    assert result.report.bad_numbers == 1
    assert len(result.frame) == 5


def test_untidy_labels_are_fixed():
    row = list(ROWS[2])
    row[3], row[4] = "  north ", "STORE"
    frame = clean(ROWS + [tuple(row[:6] + ["Hat"] + row[7:])]).frame
    assert set(frame["region"]) == {"London", "North"}
    assert set(frame["channel"]) == {"Online", "Store"}


def test_most_common_spelling_keeps_small_words():
    column = pd.Series(["East of England", "east of england", "East of England", "EAST OF ENGLAND"])
    assert set(most_common_spelling(column)) == {"East of England"}


def test_rows_are_in_date_order():
    result = clean(list(reversed(ROWS)))
    assert result.frame["order_date"].is_monotonic_increasing


def test_extra_columns_are_left_out(raw):
    frame = SalesCleaner().clean(raw.assign(notes="hi")).frame
    assert "notes" not in frame.columns


def test_report(sales):
    report = clean(ROWS + [ROWS[0]]).report
    assert report.rows_in == 7
    assert report.rows_out == 6
    assert report.dropped == 1
    assert report.lines()[0] == "Rows read:                  7"


def test_the_sample_file_cleans_as_expected():
    report = SalesCleaner().clean(CsvSalesSource(SAMPLE).load()).report
    assert report.duplicates == 12
    assert report.missing_values == 8
    assert report.bad_dates == 8
    assert report.bad_numbers == 8
    assert report.rows_out == report.rows_in - 36
