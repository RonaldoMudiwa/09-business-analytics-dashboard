"""The command line interface.

    python -m analytics demo                          the whole dashboard for the sample data
    python -m analytics summary                       KPIs and what the cleaner did
    python -m analytics breakdown --by region         totals for each region
    python -m analytics compare --month 2026-10 --vs last-year
    python -m analytics trend --forecast 6            months, average, forecasts and their check
    python -m analytics customers                     RFM segments
    python -m analytics dashboard --html data/dashboard.html --excel data/dashboard.xlsx

Filters go before the command and work with every command:
    python -m analytics --region London --from 2026-06-01 --to 2026-08-31 summary

Every command reads data/sample_sales.csv unless --data says otherwise.
"""

from __future__ import annotations

import argparse
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence, TextIO

import pandas as pd

from .breakdowns import DIMENSIONS, SORT_KEYS, Breakdown
from .cleaning import CleaningReport, SalesCleaner
from .comparison import compare, latest_month, previous_period, same_period_last_year
from .customers import DEFAULT_SEGMENTS, add_segments, customer_table, repeat_rate, segment_summary
from .dashboard import HtmlDashboard, TextDashboard, build_dashboard
from .exceptions import AnalyticsError
from .filters import DateRange, Everything, IsOneOf, SalesFilter
from .metrics import calculate_kpis
from .money import format_percent, format_pounds
from .sources import CsvSalesSource
from .trends import LinearTrend, SeasonalNaive, backtest, monthly_series, rolling_average

DEFAULT_DATA = Path("data/sample_sales.csv")


class Context:
    """What a command gets to work with while it runs."""

    def __init__(self, out: TextIO, args: argparse.Namespace) -> None:
        self.out = out
        self.args = args
        self.report: CleaningReport | None = None

    def say(self, text: str = "") -> None:
        print(text, file=self.out)

    def where(self) -> SalesFilter:
        """The filter built from --from, --to, --region, --category and --channel."""
        args = self.args
        parts: list[SalesFilter] = []
        if args.start or args.end:
            parts.append(DateRange(args.start, args.end))
        for column in ("region", "category", "channel"):
            values = getattr(args, column)
            if values:
                parts.append(IsOneOf(column, values))
        if not parts:
            return Everything()
        combined = parts[0]
        for part in parts[1:]:
            combined = combined & part
        return combined

    def sales(self) -> pd.DataFrame:
        """Clean, filtered sales. Raises an error if nothing is left."""
        result = SalesCleaner().clean(CsvSalesSource(self.args.data).load())
        self.report = result.report
        where = self.where()
        chosen = where.apply(result.frame)
        if chosen.empty:
            raise AnalyticsError(f"No sales match: {where.describe()}.")
        if not isinstance(where, Everything):
            self.say(f"Showing: {where.describe()}\n")
        return chosen


class Command(ABC):
    """One thing the user can ask for. Each command is its own small class."""

    name = ""
    help = ""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add this command's own options. Commands with none can skip it."""

    @abstractmethod
    def run(self, ctx: Context) -> None:
        """Do the job. Raise an AnalyticsError if it can't be done."""


class SummaryCommand(Command):
    name = "summary"
    help = "the main KPIs, and what the cleaner fixed or dropped"

    def run(self, ctx: Context) -> None:
        sales = ctx.sales()
        for kpi in calculate_kpis(sales):
            ctx.say(f"  {kpi.label:<16}{kpi.text:>14}")
        ctx.say(f"\n  From {sales['order_date'].min().date()} to {sales['order_date'].max().date()}")
        ctx.say("\nCleaning:")
        for line in ctx.report.lines():
            ctx.say(f"  {line}")


class BreakdownCommand(Command):
    name = "breakdown"
    help = "totals for each month, category, region, channel or product"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--by", choices=DIMENSIONS, default="category")
        parser.add_argument("--top", type=int, help="only the best N")
        parser.add_argument("--sort", choices=SORT_KEYS, default="revenue",
                            help="what --top ranks by")

    def run(self, ctx: Context) -> None:
        breakdown = Breakdown(ctx.args.by)
        sales = ctx.sales()
        table = (breakdown.top(sales, ctx.args.top, ctx.args.sort) if ctx.args.top
                 else breakdown.table(sales))
        ctx.say(f"{ctx.args.by.replace('_', ' ').capitalize():<22}{'Revenue':>14}{'Profit':>14}"
                f"{'Orders':>8}{'Units':>8}{'Share':>8}{'Margin':>8}")
        for name, row in table.iterrows():
            ctx.say(f"{str(name):<22}{format_pounds(row['revenue']):>14}"
                    f"{format_pounds(row['profit']):>14}{int(row['orders']):>8,}"
                    f"{int(row['units']):>8,}{format_percent(row['share']):>8}"
                    f"{format_percent(row['margin']):>8}")


class CompareCommand(Command):
    name = "compare"
    help = "one month against the month before, or the same month last year"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--month", help="YYYY-MM (default: the latest month)")
        parser.add_argument("--vs", choices=("previous", "last-year"), default="previous")

    def run(self, ctx: Context) -> None:
        sales = ctx.sales()
        current = DateRange.month(ctx.args.month or latest_month(sales))
        if ctx.args.vs == "previous":
            previous = previous_period(current)
        else:
            previous = same_period_last_year(current)
        ctx.say(f"{current.describe()}  vs  {previous.describe()}\n")
        for c in compare(sales, current, previous):
            ctx.say(f"  {c.label:<16}{c.current_text:>14}{c.previous_text:>14}"
                    f"  {c.arrow()} {c.percent_text()}")


class TrendCommand(Command):
    name = "trend"
    help = "revenue by month with a rolling average, and two forecasts checked on known months"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--forecast", type=int, default=3, help="months to forecast")

    def run(self, ctx: Context) -> None:
        revenue = monthly_series(ctx.sales())
        average = rolling_average(revenue, 3)
        ctx.say(f"{'Month':<10}{'Revenue':>14}{'3 month avg':>14}")
        for month, value in revenue.items():
            smooth = "" if pd.isna(average[month]) else format_pounds(average[month])
            ctx.say(f"{str(month):<10}{format_pounds(value):>14}{smooth:>14}")
        for forecaster in (LinearTrend(), SeasonalNaive()):
            ctx.say(f"\n{forecaster.name}:")
            try:
                if len(revenue) > 6:
                    ctx.say(f"  Check: {backtest(forecaster, revenue, 6).text()}")
                for month, value in forecaster.predict(revenue, ctx.args.forecast).items():
                    ctx.say(f"  {month}  {format_pounds(value):>14}")
            except AnalyticsError as error:
                # One forecast needing more history shouldn't hide the other.
                ctx.say(f"  Can't forecast: {error}")


class CustomersCommand(Command):
    name = "customers"
    help = "customer segments by recency, frequency and spend (RFM)"

    def run(self, ctx: Context) -> None:
        sales = ctx.sales()
        summary = segment_summary(add_segments(customer_table(sales)))
        meanings = {rule.name: rule.meaning for rule in DEFAULT_SEGMENTS}
        ctx.say(f"{'Segment':<18}{'Customers':>10}{'Revenue':>15}{'Share':>8}  What it means")
        for name, row in summary.iterrows():
            ctx.say(f"{name:<18}{int(row['customers']):>10,}{format_pounds(row['revenue']):>15}"
                    f"{format_percent(row['share_of_revenue']):>8}  {meanings.get(name, '')}")
        ctx.say(f"\n{format_percent(repeat_rate(sales), 0)} of customers came back for "
                "another order.")


class DashboardCommand(Command):
    name = "dashboard"
    help = "the whole dashboard; save it as a web page and/or an Excel file"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--title", default="Sales dashboard")
        parser.add_argument("--html", type=Path, help="save a web page here")
        parser.add_argument("--excel", type=Path, help="save an Excel workbook here")
        parser.add_argument("--top", type=int, default=5, help="how many top products")

    def run(self, ctx: Context) -> None:
        board = build_dashboard(ctx.sales(), ctx.args.title, ctx.where(), max(ctx.args.top, 1))
        ctx.say(TextDashboard().render(board).rstrip())
        if ctx.args.html:
            ctx.say(f"\nSaved {HtmlDashboard().save(board, ctx.args.html)}. Open it in a browser.")
        if ctx.args.excel:
            from .excel import ExcelReport  # only needed when asked for
            ctx.say(f"Saved {ExcelReport().save(board, ctx.args.excel)}.")


class DemoCommand(Command):
    name = "demo"
    help = "show the whole dashboard for the made up sample data"

    def run(self, ctx: Context) -> None:
        ctx.say("(The sample data is made up: a pretend outdoor gear shop.)\n")
        board = build_dashboard(ctx.sales(), "Outdoor shop sales", ctx.where())
        ctx.say(TextDashboard().render(board).rstrip())
        ctx.say("\nTry: python -m analytics dashboard --html data/dashboard.html")


COMMANDS: tuple[Command, ...] = (
    DemoCommand(), SummaryCommand(), BreakdownCommand(), CompareCommand(), TrendCommand(),
    CustomersCommand(), DashboardCommand(),
)


def build_parser(commands: Sequence[Command] = COMMANDS) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m analytics",
                                     description="Analyse a shop's sales.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="the sales CSV file")
    filters = parser.add_argument_group("filters (work with every command)")
    filters.add_argument("--from", dest="start", help="first day, YYYY-MM-DD")
    filters.add_argument("--to", dest="end", help="last day, YYYY-MM-DD")
    filters.add_argument("--region", action="append", help="can be given more than once")
    filters.add_argument("--category", action="append")
    filters.add_argument("--channel", action="append")
    sub = parser.add_subparsers(dest="command", metavar="command")
    for command in commands:
        child = sub.add_parser(command.name, help=command.help, description=command.help)
        command.add_arguments(child)
        child.set_defaults(handler=command)
    return parser


def main(argv: Sequence[str] | None = None, out: TextIO | None = None) -> int:
    """Run one command. Returns 0 if it worked, 1 if it didn't."""
    out = out or sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(out)
        return 0
    try:
        args.handler.run(Context(out, args))
    except AnalyticsError as error:
        print(f"Error: {error}", file=out)
        return 1
    return 0
