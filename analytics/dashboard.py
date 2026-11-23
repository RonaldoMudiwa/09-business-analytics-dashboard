"""The dashboard: everything on one page.

build_dashboard() does all the sums once and puts the results in a
Dashboard object. Renderers only show it: TextDashboard for the terminal,
HtmlDashboard for a web page with charts. That split means the numbers on
the screen and in the web page can never disagree, and adding a new
format (like Excel) never touches the sums.
"""

from __future__ import annotations

import html
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .breakdowns import Breakdown
from .charts import BarChart, TrendChart
from .comparison import Change, compare, latest_month, previous_period
from .customers import add_segments, customer_table, repeat_rate, segment_summary
from .exceptions import ValidationError
from .filters import DateRange, Everything, SalesFilter
from .metrics import KPI, calculate_kpis
from .money import format_percent, format_pounds
from .trends import (
    Backtest,
    Forecaster,
    LinearTrend,
    SeasonalNaive,
    backtest,
    monthly_series,
    rolling_average,
)


@dataclass(frozen=True)
class Dashboard:
    """Every number the dashboard shows, worked out once."""

    title: str
    showing: str
    first_day: pd.Timestamp
    last_day: pd.Timestamp
    kpis: list[KPI]
    latest_month: str
    changes: list[Change]
    monthly: pd.DataFrame          # revenue, average, profit per month
    forecast: pd.Series
    forecast_check: Backtest | None
    categories: pd.DataFrame
    regions: pd.DataFrame
    channels: pd.DataFrame
    top_products: pd.DataFrame
    segments: pd.DataFrame
    repeat_rate: float
    notes: list[str] = field(default_factory=list)


def pick_forecaster(history: pd.Series) -> tuple[Forecaster, Backtest | None]:
    """Use whichever forecast was more accurate on known months, if there's enough history."""
    if len(history) < 18:
        return LinearTrend(), None
    checks = [(f, backtest(f, history, 6)) for f in (LinearTrend(), SeasonalNaive())]
    return min(checks, key=lambda pair: pair[1].average_error)


def build_dashboard(sales: pd.DataFrame, title: str = "Sales dashboard",
                    where: SalesFilter | None = None, top: int = 5,
                    forecast_months: int = 3) -> Dashboard:
    """Work out everything the dashboard shows, for the sales the filter keeps."""
    where = where or Everything()
    chosen = where.apply(sales)
    if chosen.empty:
        raise ValidationError(f"No sales match: {where.describe()}.")
    month = latest_month(chosen)
    this_month = DateRange.month(month)
    revenue = monthly_series(chosen)
    monthly = pd.DataFrame({"revenue": revenue, "average": rolling_average(revenue, 3),
                            "profit": monthly_series(chosen, "profit_pence")})
    forecaster, check = pick_forecaster(revenue)
    notes = []
    if chosen["order_date"].max() < this_month.end:
        notes.append(f"{month} may not be finished yet: the last sale is on "
                     f"{chosen['order_date'].max().date().isoformat()}.")
    return Dashboard(
        title=title,
        showing=where.describe(),
        first_day=chosen["order_date"].min(),
        last_day=chosen["order_date"].max(),
        kpis=calculate_kpis(chosen),
        latest_month=month,
        # Both months use the same filtered sales, so it's like for like.
        changes=compare(chosen, this_month, previous_period(this_month)),
        monthly=monthly,
        forecast=forecaster.predict(revenue, forecast_months),
        forecast_check=check,
        categories=Breakdown("category").table(chosen),
        regions=Breakdown("region").table(chosen),
        channels=Breakdown("channel").table(chosen),
        top_products=Breakdown("product").top(chosen, top),
        segments=segment_summary(add_segments(customer_table(chosen))),
        repeat_rate=repeat_rate(chosen),
        notes=notes,
    )


def write_safely(path: Path, text: str) -> Path:
    """Write to a temp file first, then swap it in, so a crash never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(text)
        os.chmod(temp, 0o644)  # temp files start private; a saved report shouldn't be
        os.replace(temp, path)
    except BaseException:
        os.unlink(temp)
        raise
    return path


class DashboardRenderer(ABC):
    """Turns a Dashboard into something to look at."""

    @abstractmethod
    def render(self, board: Dashboard) -> str:
        """The whole dashboard as text."""

    def save(self, board: Dashboard, path: str | Path) -> Path:
        return write_safely(Path(path), self.render(board))


def bar(value: float, biggest: float, width: int = 24) -> str:
    """A bar made of blocks, scaled so the biggest value fills the width."""
    return "█" * round(width * value / biggest) if biggest > 0 else ""


class TextDashboard(DashboardRenderer):
    """For the terminal."""

    def render(self, board: Dashboard) -> str:
        lines = [board.title, "=" * len(board.title),
                 f"{board.first_day.date()} to {board.last_day.date()}  ({board.showing})", ""]
        for kpi in board.kpis:
            lines.append(f"  {kpi.label:<16}{kpi.text:>14}")
        lines += ["", f"{board.latest_month} compared with the month before:"]
        for c in board.changes:
            lines.append(f"  {c.label:<16}{c.current_text:>14}{c.previous_text:>14}"
                         f"  {c.arrow()} {c.percent_text()}")
        lines += ["", "Revenue by month:"]
        biggest = board.monthly["revenue"].max()
        for month, row in board.monthly.iterrows():
            lines.append(f"  {month}  {format_pounds(row['revenue']):>12}  "
                         f"{bar(row['revenue'], biggest)}")
        for month, value in board.forecast.items():
            lines.append(f"  {month}  {format_pounds(value):>12}  "
                         f"{'░' * len(bar(value, biggest))}  forecast")
        if board.forecast_check:
            lines.append(f"  (Forecast: {board.forecast_check.text()})")
        for heading, table in (("Categories", board.categories), ("Regions", board.regions),
                               ("Channels", board.channels), ("Top products", board.top_products)):
            lines += ["", f"{heading}:"]
            top = table["revenue"].max()
            for name, row in table.iterrows():
                lines.append(f"  {str(name):<20}{format_pounds(row['revenue']):>13}"
                             f"{format_percent(row['share']):>7}  {bar(row['revenue'], top, 16)}")
        lines += ["", f"Customers ({format_percent(board.repeat_rate, 0)} came back for "
                      "another order):"]
        for name, row in board.segments.iterrows():
            lines.append(f"  {str(name):<20}{int(row['customers']):>6,} customers"
                         f"{format_pounds(row['revenue']):>14}")
        lines += [""] + [f"Note: {n}" for n in board.notes]
        return "\n".join(lines).rstrip() + "\n"


def esc(value: object) -> str:
    return html.escape(str(value))


STYLE = """
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0;
       background: #fcfcfb; color: #0b0b0b; }
main { max-width: 1000px; margin: 0 auto; padding: 24px; }
h1 { margin: 0 0 4px; font-size: 26px; }
h2 { font-size: 18px; margin: 32px 0 8px; }
.muted { color: #52514e; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px;
         margin-top: 20px; }
.card { border: 1px solid #e4e3df; border-radius: 8px; padding: 12px 14px; background: #fff; }
.card .label { font-size: 13px; color: #52514e; }
.card .value { font-size: 24px; font-weight: 600; margin: 4px 0; }
.card .change { font-size: 13px; color: #52514e; }
img { max-width: 100%; height: auto; display: block; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: right; padding: 6px 8px; border-bottom: 1px solid #e4e3df; }
th:first-child, td:first-child { text-align: left; }
th { color: #52514e; font-weight: 600; }
.note { background: #fff7e0; border-left: 3px solid #eda100; padding: 8px 12px; margin-top: 16px; }
"""


class HtmlDashboard(DashboardRenderer):
    """A single web page with the charts inside it, so it can be emailed as one file."""

    def render(self, board: Dashboard) -> str:
        changes = {c.label: c for c in board.changes}
        cards = []
        for kpi in board.kpis:
            change = changes.get(kpi.label)
            line = (f"{change.arrow()} {change.percent_text()} vs month before"
                    if change else "")
            cards.append(f'<div class="card"><div class="label">{esc(kpi.label)}</div>'
                         f'<div class="value">{esc(kpi.text)}</div>'
                         f'<div class="change">{esc(line)}</div></div>')
        trend = TrendChart("Revenue by month", board.monthly["revenue"],
                           board.monthly["average"], board.forecast)
        check = (f"<p class=\"muted\">Forecast: {esc(board.forecast_check.text())}.</p>"
                 if board.forecast_check else "")
        notes = "".join(f'<div class="note">{esc(n)}</div>' for n in board.notes)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(board.title)}</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>{esc(board.title)}</h1>
<p class="muted">{esc(board.first_day.date())} to {esc(board.last_day.date())} &middot;
{esc(board.showing)} &middot; changes compare {esc(board.latest_month)} with the month before</p>
{notes}
<div class="cards">{''.join(cards)}</div>
<img src="{trend.to_data_uri()}" alt="Bar chart of revenue for each month, with a 3 month average line and a dashed forecast">
{check}
<div class="grid">
{self.section("Categories", board.categories)}
{self.section("Regions", board.regions)}
{self.section("Channels", board.channels)}
{self.section("Top products", board.top_products)}
</div>
<h2>Customers</h2>
<p class="muted">{esc(format_percent(board.repeat_rate, 0))} of customers came back for another order.</p>
{self.segment_table(board.segments)}
<h2>Month by month</h2>
{self.month_table(board.monthly)}
</main>
</body>
</html>
"""

    def section(self, heading: str, table: pd.DataFrame) -> str:
        chart = BarChart(heading, table["revenue"])
        rows = "".join(
            f"<tr><td>{esc(name)}</td><td>{esc(format_pounds(r['revenue']))}</td>"
            f"<td>{esc(format_percent(r['share']))}</td><td>{esc(format_percent(r['margin']))}</td>"
            f"<td>{int(r['orders']):,}</td></tr>" for name, r in table.iterrows())
        return (f'<section><img src="{chart.to_data_uri()}" alt="Bar chart of revenue by '
                f'{esc(heading.lower())}"><table><tr><th>{esc(heading)}</th><th>Revenue</th>'
                f"<th>Share</th><th>Margin</th><th>Orders</th></tr>{rows}</table></section>")

    @staticmethod
    def segment_table(segments: pd.DataFrame) -> str:
        rows = "".join(
            f"<tr><td>{esc(name)}</td><td>{int(r['customers']):,}</td>"
            f"<td>{esc(format_pounds(r['revenue']))}</td>"
            f"<td>{esc(format_percent(r['share_of_revenue']))}</td></tr>"
            for name, r in segments.iterrows())
        return ("<table><tr><th>Segment</th><th>Customers</th><th>Revenue</th>"
                f"<th>Share of revenue</th></tr>{rows}</table>")

    @staticmethod
    def month_table(monthly: pd.DataFrame) -> str:
        rows = "".join(
            f"<tr><td>{esc(month)}</td><td>{esc(format_pounds(r['revenue']))}</td>"
            f"<td>{esc(format_pounds(r['profit']))}</td>"
            f"<td>{esc(format_pounds(r['average']) if pd.notna(r['average']) else '-')}</td></tr>"
            for month, r in monthly.iterrows())
        return ("<table><tr><th>Month</th><th>Revenue</th><th>Profit</th>"
                f"<th>3 month average</th></tr>{rows}</table>")
