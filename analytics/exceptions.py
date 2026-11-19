"""All the errors this package can raise.

Everything inherits from AnalyticsError, so one except clause catches the lot.
"""

from __future__ import annotations


class AnalyticsError(Exception):
    """Base class for every error in this package. Never raised directly."""


class ValidationError(AnalyticsError):
    """A value isn't allowed, e.g. an end date before the start date."""


class DataError(AnalyticsError):
    """A data file is missing, or isn't in the shape we expect."""
