"""Charts, drawn with matplotlib and saved as PNG pictures.

Each chart is a small class behind the Chart base class. They use
matplotlib's Figure object directly instead of pyplot, so no chart can
leave anything behind that changes the next one.
"""

from __future__ import annotations

import base64
import io
from abc import ABC, abstractmethod

import matplotlib

matplotlib.use("Agg")  # draw to pictures, never open a window

import pandas as pd  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

# Colours picked to be easy to tell apart, including for colour blind readers.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#0b0b0b"
SOFT_INK = "#52514e"
GRID = "#e4e3df"
BACKGROUND = "#fcfcfb"


def pounds_axis(value: float, _position: int) -> str:
    """Axis labels in pounds: 2500000 pence becomes '£25k'."""
    pounds = value / 100
    return f"£{pounds / 1000:,.0f}k" if abs(pounds) >= 1000 else f"£{pounds:,.0f}"


class Chart(ABC):
    """A chart that can be turned into a PNG picture."""

    width, height = 8.0, 3.6

    def __init__(self, title: str) -> None:
        self.title = title

    @abstractmethod
    def draw(self, ax: Axes) -> None:
        """Draw the chart's marks on the axes."""

    def figure(self) -> Figure:
        fig = Figure(figsize=(self.width, self.height), dpi=100, facecolor=BACKGROUND)
        ax = fig.add_subplot()
        ax.set_facecolor(BACKGROUND)
        ax.set_title(self.title, loc="left", color=INK, fontsize=12)
        self.draw(ax)
        # Quiet axes so the data stands out.
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=SOFT_INK, labelsize=9, length=0)
        fig.tight_layout()
        return fig

    def to_png(self) -> bytes:
        buffer = io.BytesIO()
        self.figure().savefig(buffer, format="png")
        return buffer.getvalue()

    def to_data_uri(self) -> str:
        """The picture as text, so it can sit inside a web page with no separate file."""
        return "data:image/png;base64," + base64.b64encode(self.to_png()).decode("ascii")


class TrendChart(Chart):
    """Monthly revenue as bars, the rolling average as a line, and the forecast dashed."""

    def __init__(self, title: str, actual: pd.Series, average: pd.Series,
                 forecast: pd.Series | None = None) -> None:
        super().__init__(title)
        self.actual = actual
        self.average = average
        self.forecast = forecast if forecast is not None else pd.Series(dtype="float64")

    def draw(self, ax: Axes) -> None:
        months = list(self.actual.index) + list(self.forecast.index)
        x = {month: i for i, month in enumerate(months)}
        ax.bar([x[m] for m in self.actual.index], self.actual.to_numpy(), width=0.7,
               color=BLUE, label="Revenue", zorder=2)
        ax.plot([x[m] for m in self.average.index], self.average.to_numpy(), color=ORANGE,
                linewidth=2, label="3 month average", zorder=3)
        if not self.forecast.empty:
            ax.bar([x[m] for m in self.forecast.index], self.forecast.to_numpy(), width=0.7,
                   color="none", edgecolor=BLUE, linestyle="--", linewidth=1.5,
                   label="Forecast", zorder=2)
        # Label every third month so the labels don't crash into each other.
        ticks = list(range(0, len(months), 3))
        ax.set_xticks(ticks, [months[i].strftime("%b %y") for i in ticks])
        ax.yaxis.set_major_formatter(FuncFormatter(pounds_axis))
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
        # The key sits above the plot, so it never covers a bar.
        ax.legend(frameon=False, fontsize=9, labelcolor=SOFT_INK, ncol=3, loc="lower right",
                  bbox_to_anchor=(1, 1))


class BarChart(Chart):
    """Horizontal bars, biggest at the top. Good for categories, regions and products."""

    width = 5.0

    def __init__(self, title: str, values: pd.Series, money: bool = True) -> None:
        super().__init__(title)
        self.values = values
        self.money = money
        self.height = 0.5 + 0.38 * max(len(values), 1) + 0.6

    def draw(self, ax: Axes) -> None:
        ordered = self.values.iloc[::-1]  # barh draws from the bottom up
        labels = [str(label) for label in ordered.index]
        bars = ax.barh(labels, ordered.to_numpy(), height=0.6, color=BLUE, zorder=2)
        # Only the bar ends are labelled, not every gridline, so it stays easy to read.
        texts = [pounds_axis(v, 0) if self.money else f"{v:,.0f}" for v in ordered]
        ax.bar_label(bars, labels=texts, padding=4, color=SOFT_INK, fontsize=9)
        ax.set_xticks([])
        ax.margins(x=0.15)
