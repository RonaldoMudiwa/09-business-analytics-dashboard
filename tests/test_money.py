from decimal import Decimal

import pytest

from analytics import format_percent, format_pounds, to_pounds


@pytest.mark.parametrize("pence,pounds", [(1999, "19.99"), (5, "0.05"), (0, "0.00"),
                                          (12.5, "0.13"), (-250, "-2.50")])
def test_to_pounds(pence, pounds):
    assert to_pounds(pence) == Decimal(pounds)


@pytest.mark.parametrize("pence,text", [(1234567, "£12,345.67"), (99, "£0.99"), (-1050, "-£10.50")])
def test_format_pounds(pence, text):
    assert format_pounds(pence) == text


def test_format_percent():
    assert format_percent(0.256) == "25.6%"
    assert format_percent(-0.05, 0) == "-5%"
