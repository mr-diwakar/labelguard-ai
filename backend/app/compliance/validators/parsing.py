"""Deterministic parsers for declaration values. These are not legal format rules."""

from __future__ import annotations

import json
import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

_MRP_PREFIX = re.compile(r"(?i)^\s*(mrp\s*[:\-]?\s*)?(rs\.?|inr|₹)?\s*")
_MRP_SUFFIX = re.compile(r"(?i)\s*(only|/-)?\s*$")
_MRP_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")

_QTY_PATTERN = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*([A-Za-z]+)\s*$")
_QTY_NUMBER_ONLY = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*$")

UNIT_ALIASES = {
    "g": "g",
    "gm": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "ml": "ml",
    "millilitre": "ml",
    "milliliter": "ml",
    "millilitres": "ml",
    "milliliters": "ml",
    "l": "l",
    "ltr": "l",
    "litre": "l",
    "liter": "l",
    "litres": "l",
    "liters": "l",
    "pcs": "pcs",
    "pc": "pcs",
    "n": "pcs",
    "no": "pcs",
    "nos": "pcs",
    "number": "pcs",
}

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_ISO_MONTH = re.compile(r"^(\d{4})-(\d{2})$")
_MONTH_SLASH = re.compile(r"^(\d{1,2})/(\d{4})$")
_MONTH_DASH = re.compile(r"^(\d{1,2})-(\d{4})$")
_DMY_SLASH = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_DMY_DASH = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")
_YEAR_SLASH_MONTH = re.compile(r"^(\d{4})/(\d{1,2})$")


@dataclass(frozen=True)
class ParsedAmount:
    value: Decimal


@dataclass(frozen=True)
class ParsedQuantity:
    value: Decimal
    unit: str


@dataclass(frozen=True)
class ParsedDate:
    year: int
    month: int
    day: int | None = None


def parse_mrp(raw: str) -> ParsedAmount | None:
    text = _MRP_SUFFIX.sub("", _MRP_PREFIX.sub("", raw.strip()))
    text = text.replace("₹", "").replace(",", "").strip()
    if not _MRP_NUMBER.fullmatch(text):
        return None
    try:
        return ParsedAmount(Decimal(text))
    except InvalidOperation:
        return None


def parse_quantity(raw: str) -> ParsedQuantity | None:
    text = raw.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return _quantity_from_parts(payload.get("value"), payload.get("unit"))

    match = _QTY_PATTERN.fullmatch(text)
    if match:
        return _quantity_from_parts(match.group(1), match.group(2))

    return None


def parse_quantity_or_number(raw: str) -> tuple[ParsedQuantity | None, bool]:
    """
    Returns (parsed, number_without_unit).

    A bare number is structurally incomplete, not a legal unit-law finding.
    """
    parsed = parse_quantity(raw)
    if parsed is not None:
        return parsed, False
    if _QTY_NUMBER_ONLY.fullmatch(raw.strip()):
        return None, True
    return None, False


def _quantity_from_parts(value: object, unit: object) -> ParsedQuantity | None:
    if value is None or unit is None:
        return None
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    alias = UNIT_ALIASES.get(str(unit).strip().lower())
    if alias is None:
        return None
    return ParsedQuantity(value=amount, unit=alias)


def parse_declaration_date(raw: str) -> ParsedDate | str:
    """
    Returns a parsed date, 'impossible', or 'malformed'.

    Three-part slash/dash dates are read as day/month/year (common Indian order).
    This is a parse convention, not a Legal Metrology display rule.
    """
    text = raw.strip()

    match = _ISO_DATE.fullmatch(text)
    if match:
        return _full_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    match = _ISO_MONTH.fullmatch(text) or _YEAR_SLASH_MONTH.fullmatch(text)
    if match:
        return _month_year(int(match.group(1)), int(match.group(2)))

    match = _MONTH_SLASH.fullmatch(text) or _MONTH_DASH.fullmatch(text)
    if match:
        return _month_year(int(match.group(2)), int(match.group(1)))

    match = _DMY_SLASH.fullmatch(text) or _DMY_DASH.fullmatch(text)
    if match:
        return _full_date(int(match.group(3)), int(match.group(2)), int(match.group(1)))

    return "malformed"


def _month_year(year: int, month: int) -> ParsedDate | str:
    if year < 1 or month < 1 or month > 12:
        return "impossible"
    return ParsedDate(year=year, month=month)


def _full_date(year: int, month: int, day: int) -> ParsedDate | str:
    if year < 1 or month < 1 or month > 12 or day < 1:
        return "impossible"
    last = monthrange(year, month)[1]
    if day > last:
        return "impossible"
    date(year, month, day)
    return ParsedDate(year=year, month=month, day=day)
