"""Cleaning raw sales rows so the numbers can be trusted.

Real exports are messy: copies of the same row, dates that aren't dates,
"  london " next to "London", a quantity of -1. If we added those up as
they are, every total would be a little bit wrong. The cleaner fixes what
it safely can, drops what it can't, and keeps count of everything, so you
can see exactly what happened to your data.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .sources import REQUIRED_COLUMNS

TEXT_COLUMNS = ("order_id", "customer_id", "region", "channel", "category", "product")
# Columns where "london" and "London" mean the same thing.
LABEL_COLUMNS = ("region", "channel", "category", "product")
WHOLE_NUMBER_COLUMNS = ("quantity", "unit_price_pence", "unit_cost_pence")


@dataclass(frozen=True)
class CleaningReport:
    """What the cleaner did, row by row."""

    rows_in: int
    duplicates: int
    missing_values: int
    bad_dates: int
    bad_numbers: int
    rows_out: int

    @property
    def dropped(self) -> int:
        return self.rows_in - self.rows_out

    def lines(self) -> list[str]:
        return [
            f"Rows read:            {self.rows_in:>7,}",
            f"Exact copies removed: {self.duplicates:>7,}",
            f"Missing values:       {self.missing_values:>7,}",
            f"Dates that aren't:    {self.bad_dates:>7,}",
            f"Bad numbers:          {self.bad_numbers:>7,}",
            f"Rows kept:            {self.rows_out:>7,}",
        ]


@dataclass(frozen=True)
class CleanResult:
    frame: pd.DataFrame
    report: CleaningReport


def most_common_spelling(column: pd.Series) -> pd.Series:
    """Swap every spelling for the one used most often, ignoring case.

    "LONDON", "london" and "London" all become "London" if that's how it's
    usually written. This is safer than .title(), which would turn
    "East of England" into "East Of England".
    """
    counts = column.value_counts()
    best: dict[str, str] = {}
    # value_counts is most common first, so the first spelling we see wins.
    for spelling in counts.index:
        best.setdefault(spelling.lower(), spelling)
    return column.map(lambda value: best[value.lower()])


class SalesCleaner:
    """Turns raw rows into clean, typed rows with money worked out."""

    def clean(self, raw: pd.DataFrame) -> CleanResult:
        frame = raw.loc[:, list(REQUIRED_COLUMNS)].copy()
        rows_in = len(frame)

        for column in TEXT_COLUMNS:
            frame[column] = frame[column].fillna("").astype(str).str.strip()
        frame["order_date"] = frame["order_date"].fillna("").astype(str).str.strip()
        for column in WHOLE_NUMBER_COLUMNS:
            frame[column] = frame[column].fillna("").astype(str).str.strip()

        # Copies of the same row, e.g. an export that was run twice.
        before = len(frame)
        frame = frame.drop_duplicates()
        duplicates = before - len(frame)

        # Rows with a gap in any column we need.
        missing = (frame == "").any(axis=1)
        frame = frame[~missing]

        dates = pd.to_datetime(frame["order_date"], format="%Y-%m-%d", errors="coerce")
        bad_date = dates.isna()
        frame = frame[~bad_date].assign(order_date=dates[~bad_date])

        numbers = {c: pd.to_numeric(frame[c], errors="coerce") for c in WHOLE_NUMBER_COLUMNS}
        good = (numbers["quantity"] > 0) & (numbers["unit_price_pence"] >= 0) & \
               (numbers["unit_cost_pence"] >= 0)
        for values in numbers.values():
            # Must be a whole number: 2 is fine, 2.5 isn't.
            good &= values.notna() & (values == values.round())
        frame = frame[good].copy()
        for column in WHOLE_NUMBER_COLUMNS:
            frame[column] = numbers[column][good].astype("int64")

        for column in LABEL_COLUMNS:
            frame[column] = most_common_spelling(frame[column])

        frame = add_money_columns(frame).sort_values(["order_date", "order_id"],
                                                     kind="stable").reset_index(drop=True)
        report = CleaningReport(rows_in, duplicates, int(missing.sum()), int(bad_date.sum()),
                                int((~good).sum()), len(frame))
        return CleanResult(frame, report)


def add_money_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Revenue, cost and profit for each row, in whole pennies, plus the month."""
    return frame.assign(
        revenue_pence=frame["quantity"] * frame["unit_price_pence"],
        cost_pence=frame["quantity"] * frame["unit_cost_pence"],
        profit_pence=frame["quantity"] * (frame["unit_price_pence"] - frame["unit_cost_pence"]),
        month=frame["order_date"].dt.to_period("M"),
    )
