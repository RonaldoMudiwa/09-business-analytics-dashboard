"""Makes data/sample_sales.csv: MADE UP sales for a pretend outdoor gear shop.

None of it is real. It's made with a fixed seed, so running this again gives
exactly the same file. It has the patterns a real shop would have (busier
summers and Decembers, slow growth, some loyal customers) and a few messy
rows on purpose, so the cleaning code has something to clean.

    python tools/make_sample_data.py
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import numpy as np

SEED = 9
START = date(2025, 1, 1)
END = date(2026, 10, 31)
OUT = Path(__file__).resolve().parent.parent / "data" / "sample_sales.csv"

# product: (category, price in pence, cost in pence)
PRODUCTS = {
    "Two Person Tent": ("Camping", 12999, 7400),
    "Family Tent": ("Camping", 29999, 17500),
    "Sleeping Bag": ("Camping", 5499, 2600),
    "Camping Stove": ("Camping", 3499, 1700),
    "Walking Boots": ("Footwear", 8999, 4300),
    "Trail Shoes": ("Footwear", 6999, 3200),
    "Wellies": ("Footwear", 2999, 1300),
    "Waterproof Jacket": ("Clothing", 9999, 4100),
    "Fleece": ("Clothing", 3999, 1600),
    "Thermal Base Layer": ("Clothing", 2499, 900),
    "Walking Socks": ("Clothing", 1299, 400),
    "Day Rucksack": ("Accessories", 4499, 2000),
    "Head Torch": ("Accessories", 1999, 800),
    "Water Bottle": ("Accessories", 1499, 500),
    "Map Case": ("Accessories", 999, 300),
}
REGIONS = ["London", "South East", "East of England", "Midlands", "North", "Scotland"]
REGION_WEIGHTS = [0.24, 0.2, 0.16, 0.16, 0.15, 0.09]
# How busy each month is compared with an average month.
SEASON = {1: 0.7, 2: 0.7, 3: 0.85, 4: 1.0, 5: 1.15, 6: 1.3, 7: 1.4, 8: 1.35, 9: 1.0,
          10: 0.85, 11: 1.0, 12: 1.45}
COLUMNS = ["order_id", "order_date", "customer_id", "region", "channel", "category",
           "product", "quantity", "unit_price_pence", "unit_cost_pence"]


def make_rows(rng: np.random.Generator) -> list[list]:
    names = list(PRODUCTS)
    customers = [f"C{n:04d}" for n in range(1, 601)]
    # A few customers buy far more often than the rest, like real loyal customers.
    loyalty = rng.pareto(1.5, len(customers)) + 1
    loyalty = loyalty / loyalty.sum()
    home = {c: rng.choice(REGIONS, p=REGION_WEIGHTS) for c in customers}
    rows = []
    order_number = 10000
    day = START
    while day <= END:
        months_in = (day.year - START.year) * 12 + day.month - 1
        busy = 4.0 * SEASON[day.month] * (1 + 0.015 * months_in)
        for _ in range(rng.poisson(busy)):
            order_number += 1
            customer = rng.choice(customers, p=loyalty)
            channel = "Online" if rng.random() < 0.62 else "Store"
            for product in rng.choice(names, size=rng.integers(1, 4), replace=False):
                category, price, cost = PRODUCTS[product]
                quantity = 1 if rng.random() < 0.8 else int(rng.integers(2, 4))
                rows.append([f"ORD{order_number}", day.isoformat(), customer, home[customer],
                             channel, category, product, quantity, price, cost])
        day += timedelta(days=1)
    return rows


def add_mess(rows: list[list], rng: np.random.Generator) -> list[list]:
    """Spoil a few rows the way real exports often are."""
    messy = [list(row) for row in rows]
    picks = rng.choice(len(messy), size=40, replace=False)
    for n, i in enumerate(picks):
        row = messy[i]
        kind = n % 5
        if kind == 0:
            row[7] = ""                      # quantity missing
        elif kind == 1:
            row[1] = "not a date"
        elif kind == 2:
            row[7] = -1                      # a refund line typed in by mistake
        elif kind == 3:
            row[3] = f"  {row[3].lower()} "  # untidy spacing and case
        else:
            row[4] = row[4].upper()
    # A few exact copies, like an export that was run twice.
    for i in rng.choice(len(messy), size=12, replace=False):
        messy.append(list(messy[i]))
    return messy


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = add_mess(make_rows(rng), rng)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
