"""
Deterministic text normalisation for declaration extraction (Phase 15).

Pure, side-effect-free helpers. No legal interpretation and no LLM: only Unicode
normalisation, script-aware digit handling, and *explainable* OCR-confusion
detection. The rule for numbers is deliberate -- a character an OCR pass commonly
confuses for a digit (``"5O"``) is flagged as ambiguous and a corrected candidate is
offered ALONGSIDE the original; it is never silently rewritten.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_PURE_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")

# Devanagari digits -> ASCII. Indian labels are frequently bilingual and may print
# the numeric declaration in Devanagari digits; the value is script-independent.
_DEVANAGARI_DIGITS = {ord(char): str(index) for index, char in enumerate("०१२३४५६७८९")}

# Characters an OCR pass commonly confuses for digits, mapped to the digit they most
# likely are. Used ONLY to detect ambiguity and to offer a corrected candidate --
# never to silently rewrite a numeric declaration.
OCR_DIGIT_CONFUSIONS: dict[str, str] = {
    "O": "0",
    "o": "0",
    "D": "0",
    "Q": "0",
    "l": "1",
    "I": "1",
    "i": "1",
    "|": "1",
    "Z": "2",
    "S": "5",
    "s": "5",
    "G": "6",
    "B": "8",
    "g": "9",
    "q": "9",
}

# Month names/abbreviations -> month number. Extraction converts a month-name date
# ("MAY 2024") into a numeric form the engine's parser understands; the engine
# remains the authority on whether that date is legally valid.
_MONTHS: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# Quantity unit aliases -> canonical unit. The canonical outputs (g, kg, mg, ml, l,
# pcs) are a DELIBERATE subset chosen so a DETECTED net-quantity string is always
# re-parseable by the engine's own ``parse_quantity``; a dedicated test asserts this
# stays true, so extraction never emits a unit the engine cannot read.
_QUANTITY_UNITS: dict[str, str] = {
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "millilitre": "ml", "milliliter": "ml",
    "millilitres": "ml", "milliliters": "ml",
    "l": "l", "ltr": "l", "litre": "l", "liter": "l", "litres": "l", "liters": "l",
    "pc": "pcs", "pcs": "pcs", "piece": "pcs", "pieces": "pcs",
    "n": "pcs", "no": "pcs", "nos": "pcs", "number": "pcs",
}


def normalize_text(text: str) -> str:
    """NFKC-normalise, map Devanagari digits to ASCII, and collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DEVANAGARI_DIGITS)
    return _WHITESPACE.sub(" ", text).strip()


def is_pure_number(token: str) -> bool:
    """True when the trimmed token is a plain (optionally signed/decimal) number."""
    return bool(_PURE_NUMBER.fullmatch(token.strip()))


def contains_digit_confusion(token: str) -> bool:
    """True when a token mixes real digits with OCR-confusable characters.

    This is the signal that a numeric declaration was *probably misread* (e.g.
    ``"5O"``, ``"l0"``). A token with no real digit is not treated as a misread
    number, because a fully-alphabetic token is too ambiguous to guess from.
    """
    core = token.replace(",", "").replace(".", "").replace(" ", "")
    has_digit = any(char.isdigit() for char in core)
    has_confusable = any(char in OCR_DIGIT_CONFUSIONS for char in core)
    return has_digit and has_confusable


def correct_digit_confusion(token: str) -> str:
    """Best-effort mapping of confusable characters to digits.

    The result is a *candidate* offered next to the original, never a silent
    replacement; callers must keep the status UNCERTAIN.
    """
    return "".join(OCR_DIGIT_CONFUSIONS.get(char, char) for char in token)


def month_number(name: str) -> int | None:
    """Return the month number for a month name/abbreviation, else None."""
    return _MONTHS.get(name.strip().lower())


def canonical_quantity_unit(unit: str) -> str | None:
    """Return the engine-parseable canonical unit for a raw unit token, else None."""
    return _QUANTITY_UNITS.get(unit.strip().lower().rstrip("."))
