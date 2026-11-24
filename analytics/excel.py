"""Saving the dashboard as an Excel workbook, one sheet per table.

Managers live in Excel. Money is saved as real numbers in pounds with a £
format (not as text like "£1,234.56"), so they can still add things up
and make their own charts.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from .dashboard import Dashboard
from .money import to_pounds

POUNDS = '"£"#,##0.00'
PERCENT = "0.0%"
WHOLE = "#,##0"


def pounds(pence: float) -> float:
    return float(to_pounds(pence))


class ExcelReport:
    """Writes a Dashboard to an .xlsx file."""

    def save(self, board: Dashboard, path: str | Path) -> Path:
        path = Path(path)
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        book = self.build(board)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Saved to a temp file first, then swapped in, so a crash never leaves half a file.
        handle, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        os.close(handle)
        try:
            book.save(temp)
            os.chmod(temp, 0o644)  # temp files start private; a saved report shouldn't be
            os.replace(temp, path)
        except BaseException:
            os.unlink(temp)
            raise
        return path

    def build(self, board: Dashboard) -> Workbook:
        book = Workbook()
        summary = book.active
        summary.title = "Summary"
        self.summary(summary, board)
        self.monthly(book.create_sheet("Monthly"), board)
        for name, table in (("Categories", board.categories), ("Regions", board.regions),
                            ("Channels", board.channels), ("Top products", board.top_products)):
            self.breakdown(book.create_sheet(name), name, table)
        self.customers(book.create_sheet("Customers"), board)
        return book

    def summary(self, sheet: Worksheet, board: Dashboard) -> None:
        sheet.append([board.title])
        sheet["A1"].font = Font(bold=True, size=14)
        sheet.append([f"{board.first_day.date()} to {board.last_day.date()} ({board.showing})"])
        sheet.append([])
        sheet.append(["KPI", "All time", board.latest_month, "Month before", "Change"])
        # Counted after adding it, because a blank row above doesn't count in max_row.
        header_row = sheet.max_row
        changes = {c.label: c for c in board.changes}
        for kpi in board.kpis:
            change = changes[kpi.label]
            values = [kpi.value, change.current, change.previous]
            if kpi.is_money:
                values = [pounds(v) for v in values]
            sheet.append([kpi.label, *values, change.percent_text()])
            style = POUNDS if kpi.is_money else PERCENT if change.is_rate else WHOLE
            for column in "BCD":
                sheet[f"{column}{sheet.max_row}"].number_format = style
        for note in board.notes:
            sheet.append([])
            sheet.append([f"Note: {note}"])
        self.finish(sheet, header_row)

    def monthly(self, sheet: Worksheet, board: Dashboard) -> None:
        sheet.append(["Month", "Revenue", "Profit", "3 month average", "Forecast"])
        for month, row in board.monthly.iterrows():
            average = None if pd.isna(row["average"]) else pounds(row["average"])
            sheet.append([str(month), pounds(row["revenue"]), pounds(row["profit"]), average, None])
        for month, value in board.forecast.items():
            sheet.append([str(month), None, None, None, pounds(value)])
        self.format_columns(sheet, {"B": POUNDS, "C": POUNDS, "D": POUNDS, "E": POUNDS})
        self.finish(sheet)

    def breakdown(self, sheet: Worksheet, name: str, table: pd.DataFrame) -> None:
        sheet.append([name, "Revenue", "Profit", "Orders", "Units", "Share", "Margin"])
        for label, row in table.iterrows():
            sheet.append([str(label), pounds(row["revenue"]), pounds(row["profit"]),
                          int(row["orders"]), int(row["units"]), float(row["share"]),
                          float(row["margin"])])
        self.format_columns(sheet, {"B": POUNDS, "C": POUNDS, "D": WHOLE, "E": WHOLE,
                                    "F": PERCENT, "G": PERCENT})
        self.finish(sheet)

    def customers(self, sheet: Worksheet, board: Dashboard) -> None:
        sheet.append(["Segment", "Customers", "Revenue", "Share of revenue"])
        for name, row in board.segments.iterrows():
            sheet.append([str(name), int(row["customers"]), pounds(row["revenue"]),
                          float(row["share_of_revenue"])])
        sheet.append([])
        sheet.append(["Came back for another order", board.repeat_rate])
        sheet.cell(sheet.max_row, 2).number_format = PERCENT
        self.format_columns(sheet, {"B": WHOLE, "C": POUNDS, "D": PERCENT}, last=sheet.max_row - 2)
        self.finish(sheet)

    @staticmethod
    def format_columns(sheet: Worksheet, formats: dict[str, str], last: int | None = None) -> None:
        for row in range(2, (last or sheet.max_row) + 1):
            for column, style in formats.items():
                sheet[f"{column}{row}"].number_format = style

    @staticmethod
    def finish(sheet: Worksheet, header_row: int = 1) -> None:
        """Bold headings, headings stay put when scrolling, and columns wide enough to read."""
        for cell in sheet[header_row]:
            cell.font = Font(bold=True)
        sheet.freeze_panes = sheet.cell(header_row + 1, 1)
        for index, column in enumerate(sheet.columns, start=1):
            longest = max((len(str(c.value)) for c in column if c.value is not None), default=8)
            sheet.column_dimensions[get_column_letter(index)].width = min(max(longest + 2, 10), 45)
