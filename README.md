# Business Analytics Dashboard

A Python program that reads a shop's sales, cleans them, and works out the
numbers a manager wants on one page: totals, trends, best sellers, regions
and customers.

Project 9 of a 12 week portfolio. Weeks 1 to 8 covered OOP, databases, web
APIs, NLP and search. This week is about data analysis with Pandas.

## Status

Day 4 of 7. Reading sales files, cleaning messy rows with a report of what
was fixed, money kept in whole pennies, KPIs, filters, breakdowns, pivot
tables, comparing periods, trends with two forecasts that are checked on
real months, and customer segments. 133 tests.

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

## Breakdowns

A total says "we took £534k". A breakdown says where it came from.

```python
from analytics import Breakdown, pivot

Breakdown("category").table(sales)            # one row per category
Breakdown("month").table(sales)               # one row per month, in date order
Breakdown("product").top(sales, 5, by="units")
pivot(sales, "region", "category")            # regions down the side, categories across
```

```
              revenue    profit  orders  units     share    margin
category
Camping      28667311  12559511    1476   2189  0.536025  0.438113
Footwear     10080418   5409118    1101   1582  0.188485  0.536597
Clothing      9718296   5896096    1506   2204  0.181714  0.606701
Accessories   5015285   3005985    1468   2215  0.093776  0.599365
```

(Money is in pennies here. The dashboard on Day 5 shows pounds.)

This is pandas' `groupby`: put the rows into piles by one column, then add
up each pile. It's like sorting receipts into envelopes, one per category,
and totalling each envelope. `share` is each pile's part of all revenue,
and `margin` is its profit for every £1 taken.

Camping brings in over half the money but has the lowest margin. Clothing
and accessories make more profit per £1. That's the kind of thing a
breakdown shows that a total can't.

You can break down by `month`, `category`, `region`, `channel`, `product`
or `customer_id`. `pivot()` makes a grid like a spreadsheet pivot table,
with a Total row and column.

## Comparing periods

"We took £25k in October" means little on its own. Compared with
September, it means something.

```python
from analytics import DateRange, compare, latest_month, previous_period

october = DateRange.month(latest_month(sales))
for c in compare(sales, october, previous_period(october)):
    print(f"{c.label:<15}{c.current_text:>12}{c.previous_text:>12}  {c.arrow()} {c.percent_text()}")
```

```
Revenue          £25,718.29  £21,728.39  ▲ +18.4%
Gross profit     £12,721.29  £11,247.39  ▲ +13.1%
Profit margin         49.5%       51.8%  ▼ -2.3 pts
Orders                  148         142  ▲ +4.2%
Average order       £173.77     £153.02  ▲ +13.6%
Customers               114          97  ▲ +17.5%
Units sold              371         361  ▲ +2.8%
```

- `previous_period()` gives the same length of time straight before. A
  whole month gives the whole month before, even though months have
  different numbers of days.
- `same_period_last_year()` gives October 2025 for October 2026. A 29
  February becomes 28 February.
- **The margin shows "pts" (percentage points), not %.** If the margin
  goes from 51.8% to 49.5%, saying "-4.4%" would confuse everyone. "-2.3
  pts" says what really happened.
- If there was nothing before, the change says "new" instead of dividing
  by zero.

## Trends and forecasts

```python
from analytics import LinearTrend, SeasonalNaive, backtest, monthly_series, rolling_average

revenue = monthly_series(sales)          # one total per month, gaps filled with 0
smooth = rolling_average(revenue, 3)     # each month averaged with the two before
for forecaster in (LinearTrend(), SeasonalNaive()):
    print(backtest(forecaster, revenue, holdout=6).text())
    print(forecaster.predict(revenue, 3))
```

```
Straight line trend: off by 16.5% on average over 6 months
Same month last year, plus growth: off by 13.7% on average over 6 months
```

Monthly numbers jump about. A **rolling average** smooths them out, like
judging your weight by the week instead of by the day.

There are two forecasts behind a `Forecaster` base class:

| Forecaster | How it guesses |
| --- | --- |
| `LinearTrend` | Draws the straight line that best fits the past (numpy's `polyfit`) and carries it on |
| `SeasonalNaive` | Next December will be like last December, times however much the shop grew in the last year |

**`backtest()` checks them honestly.** It hides the last 6 months, asks
each forecaster to guess them, then compares with what really happened.
It's like a practice exam: the answers exist, we just don't look until the
forecast is written. On this data the seasonal one wins, because an
outdoor shop's summers and Decembers matter more than its slow growth. A
straight line can't see seasons at all.

Neither is clever, and that's on purpose. A simple forecast you've
checked is worth more than a fancy one you haven't. Forecasts never go
below £0.

## Customers

```python
from analytics import add_segments, customer_table, repeat_rate, segment_summary

customers = add_segments(customer_table(sales))
print(segment_summary(customers))
print(f"{repeat_rate(sales):.0%} of customers came back")
```

```
                  customers   revenue  share_of_revenue
segment
Champions               110  287407.0              53.7
Loyal                    80   89946.0              16.8
New or returning         28    6439.0               1.2
At risk                  53   31191.0               5.8
Lost                    114   26961.0               5.0
Steady                  180   92871.0              17.4
```

(Revenue rounded to pounds and the share shown as a percentage here.)

This is **RFM**, a method real shops use:

- **Recency:** how long since they last bought. Recent is good.
- **Frequency:** how many orders they've made. More is good.
- **Monetary:** how much they've spent. More is good.

Each customer gets 1 to 3 for each, by which third of customers they're
in. Then simple rules, checked from the top, put them in a group:

| Segment | Rule | What a shop might do |
| --- | --- | --- |
| Champions | Recent and frequent | Thank them, early access to sales |
| Loyal | Frequent | Loyalty points |
| New or returning | Recent but only one order | A welcome offer to bring them back |
| At risk | Used to buy often, not lately | A "we miss you" discount |
| Lost | Few orders, long ago | Not worth chasing hard |
| Steady | Everyone else | Normal emails |

It's like a gym sorting members into "comes every week", "used to come"
and "just joined", so each group gets the right message. Here 110
champions (about a fifth of customers) bring in over half the money.

Each segment is a `SegmentRule` with a name, a meaning and a test, so
the rules can be swapped without touching the code that applies them.

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
