"""Inspection dates are calendar dates. Aware datetimes are converted to UTC first."""

from datetime import date, datetime, timezone


def as_inspection_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).date()
        return value.date()

    return value
