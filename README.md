# Business Analytics Dashboard

A Python program that reads a shop's sales, cleans them, and works out the
numbers a manager wants on one page: totals, trends, best sellers, regions
and customers.

Project 9 of a 12 week portfolio. Weeks 1 to 8 covered OOP, databases, web
APIs, NLP and search. This week is about data analysis with Pandas.

## Status

Day 2 of 7. Reading sales files, cleaning messy rows with a report of what
was fixed, money kept in whole pennies, KPIs, and filters that can be
combined. 67 tests.

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
pytest --cov
```

## The data

`data/sample_sales.csv` is **made up**. It's the sales of a pretend outdoor
gear shop from January 2025 to October 2026, made by
`tools/make_sample_data.py` with a fixed seed, so running it again gives
exactly the same file. It has the patterns a real shop would have (busier
summers and Decembers, slow growth, a few very loyal customers) and some
messy rows on purpose, so the cleaning code has something to do.

| Column | Example | Notes |
| --- | --- | --- |
| `order_id` | ORD10003 | One order can have several rows, one per product |
| `order_date` | 2025-01-03 | |
| `customer_id` | C0420 | |
| `region` | South East | |
| `channel` | Online or Store | |
| `category` | Clothing | |
| `product` | Waterproof Jacket | |
| `quantity` | 3 | |
| `unit_price_pence` | 9999 | £99.99 |
| `unit_cost_pence` | 4100 | What the shop paid for it |

## Reading the data

```python
from analytics import CsvSalesSource, SalesCleaner

result = SalesCleaner().clean(CsvSalesSource("data/sample_sales.csv").load())
sales = result.frame                  # a clean pandas DataFrame
print("\n".join(result.report.lines()))
```

`SalesSource` is the base class. `CsvSalesSource` reads a file and
`DataFrameSource` wraps data that's already in memory (handy for tests). A
database or a web API could be added later as one more class.

The CSV is read with every column as text on purpose. Pandas guessing the
types would hide problems, like a quantity of "two". The cleaner decides
what's a real number or date.

## Cleaning

Real exports are messy. If we added them up as they are, every total would
be a little bit wrong. The cleaner fixes what it safely can, drops what it
can't, and counts everything:

```
Rows read:              6,386
Exact copies removed:      12
Missing values:             8
Dates that aren't:          8
Bad numbers:                8
Rows kept:              6,350
```

| Problem | Example | What happens |
| --- | --- | --- |
| Exact copies | An export run twice | Removed |
| Gaps | No quantity | Row dropped |
| Not a date | "not a date", "05/01/2026" | Row dropped. Only `YYYY-MM-DD` is accepted, because 05/01 could be May or January |
| Bad numbers | -1, 0, "two", 1.5 | Row dropped. Quantities must be whole and above 0 |
| Untidy labels | "  london ", "STORE" | Fixed to the spelling used most often |

Why "the spelling used most often" and not just Title Case? Because
`.title()` would turn "East of England" into "East Of England". Picking
the most common spelling keeps the data's own style.

Each clean row also gets `revenue_pence`, `cost_pence`, `profit_pence` and
the `month` it belongs to.

## Money in whole pennies

Prices are stored as whole pennies (`9999`, not `99.99`), and only turned
into pounds when shown (`format_pounds(9999)` gives `£99.99`).

Computers store decimals like 0.1 slightly wrongly, so adding up thousands
of prices as floats can end up a penny out. Whole numbers are always
exact. It's like a till counting coins instead of guessing their weight.

## KPIs

KPI stands for key performance indicator: the handful of numbers a manager
checks first.

```python
from analytics import calculate_kpis

for kpi in calculate_kpis(sales):
    print(f"{kpi.label:<16}{kpi.text:>14}")
```

```
Revenue            £534,813.10
Gross profit       £268,707.10
Profit margin            50.2%
Orders                   3,205
Average order          £166.87
Customers                  565
Units sold               8,190
```

| KPI | What it means |
| --- | --- |
| Revenue | All the money taken |
| Gross profit | Revenue minus what the shop paid for the stock |
| Profit margin | How much of each £1 taken is profit. 50% means 50p in every £1 |
| Orders | How many orders. One order can have several rows, one per product, so order ids are counted, not rows |
| Average order | What a customer spends in one go |
| Customers | How many different customers bought something |
| Units sold | How many items went out of the door |

Each KPI is its own small class behind the `Metric` base class, with one
job: work out its number, and show it nicely (money metrics show pounds,
the margin shows a percentage). Adding a new KPI means adding one class.
Every metric copes with no sales at all and gives 0, rather than crashing
with a divide by zero.

## Filters

```python
from analytics import DateRange, IsOneOf

summer_london = DateRange("2026-06-01", "2026-08-31") & IsOneOf("region", ["London"])
print(summer_london.describe())     # 2026-06-01 to 2026-08-31 and region is London
calculate_kpis(summer_london.apply(sales))
```

Filters work like the filter buttons on a shopping site, stacked on top of
each other. `&` means "and", `|` means "or", and `~` means "not".

| Filter | Keeps |
| --- | --- |
| `DateRange(start, end)` | Sales between two dates, both days included. Either end can be left open |
| `DateRange.month("2026-10")` | One whole month |
| `IsOneOf(column, values)` | e.g. region is London or North. Ignores case |
| `Everything()` | Every row |

Every filter can describe itself in plain English, so a report can say
exactly what it's showing.

## Week plan

| Day | Focus |
| --- | --- |
| 1 | Reading sales files, cleaning, money in pennies |
| 2 | KPIs (revenue, profit, orders, average order) and filters |
| 3 | Breakdowns by month, category, region and product, and period comparisons |
| 4 | Trends, a simple forecast, and customer segments |
| 5 | Charts and an HTML dashboard |
| 6 | Command line and Excel export |
| 7 | End to end tests and README |
