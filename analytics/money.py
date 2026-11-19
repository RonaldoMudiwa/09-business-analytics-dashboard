"""Money is kept as whole pennies, and only turned into pounds for showing.

Why? Computers store decimals like 0.1 slightly wrongly, so adding up
thousands of prices as floats can end up a penny out. Whole numbers are
always exact. It's like a till counting coins instead of guessing weights.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def to_pounds(pence: int | float) -> Decimal:
    """1999 becomes Decimal('19.99'). Halves round up, like a shop would."""
    return (Decimal(str(pence)) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_pounds(pence: int | float) -> str:
    """1234567 becomes '£12,345.67'. Negative amounts get a minus sign at the front."""
    pounds = to_pounds(pence)
    sign = "-" if pounds < 0 else ""
    return f"{sign}£{abs(pounds):,.2f}"


def format_percent(value: float, places: int = 1) -> str:
    """0.256 becomes '25.6%'."""
    return f"{value * 100:.{places}f}%"
