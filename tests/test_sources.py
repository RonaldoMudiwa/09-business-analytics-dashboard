import pytest

from analytics import REQUIRED_COLUMNS, CsvSalesSource, DataError, DataFrameSource, SalesSource

from .conftest import SAMPLE


def test_reads_the_sample_file():
    frame = CsvSalesSource(SAMPLE).load()
    assert isinstance(CsvSalesSource(SAMPLE), SalesSource)
    assert list(frame.columns) == list(REQUIRED_COLUMNS)
    assert len(frame) > 6000


def test_everything_is_read_as_text(tmp_path):
    path = tmp_path / "s.csv"
    path.write_text(",".join(REQUIRED_COLUMNS) + "\nA1,2026-01-01,C1,London,Online,Camping,Tent,1,100,50\n")
    frame = CsvSalesSource(path).load()
    assert frame.loc[0, "quantity"] == "1"


def test_column_names_are_tidied(tmp_path):
    path = tmp_path / "s.csv"
    path.write_text(",".join(f" {c.upper()} " for c in REQUIRED_COLUMNS) + "\n",
                    encoding="utf-8-sig")
    assert list(CsvSalesSource(path).load().columns) == list(REQUIRED_COLUMNS)


def test_missing_file(tmp_path):
    with pytest.raises(DataError, match="No file"):
        CsvSalesSource(tmp_path / "nope.csv").load()


def test_missing_columns(tmp_path):
    path = tmp_path / "s.csv"
    path.write_text("order_id,order_date\nA1,2026-01-01\n")
    with pytest.raises(DataError, match="missing these columns: customer_id, region"):
        CsvSalesSource(path).load()


def test_empty_file(tmp_path):
    path = tmp_path / "s.csv"
    path.write_text("")
    with pytest.raises(DataError, match="couldn't be read"):
        CsvSalesSource(path).load()


def test_data_frame_source_gives_a_copy(raw):
    source = DataFrameSource(raw)
    copy = source.load()
    copy.loc[0, "product"] = "Changed"
    assert source.load().loc[0, "product"] == "Tent"


def test_data_frame_source_checks_columns(raw):
    with pytest.raises(DataError, match="The data is missing"):
        DataFrameSource(raw.drop(columns=["region"]))
