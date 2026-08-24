"""Date and category matching. No validator logic lives here."""

from datetime import date
from typing import Any

from app.core.enums import RuleStatus, VerificationStatus


def is_effective_on(effective_from: date, effective_to: date | None, on_date: date) -> bool:
    if on_date < effective_from:
        return False

    if effective_to is not None and on_date > effective_to:
        return False

    return True


def context_category_tokens(category: str, is_imported: bool = False) -> set[str]:
    tokens = {category.upper()}
    if is_imported:
        tokens.add("IMPORTED_PRODUCT")
    return tokens


def matches_category(rule_category: str, applicability: dict[str, Any] | None, requested: str | None) -> bool:
    """
    LabelGuard product categories are an application filter, not a legal classification.

    A rule with applies_to_categories=["*"] may still list legal exclusions in the same JSON.
    """
    if requested is None:
        return True

    if applicability:
        excluded = {item.upper() for item in applicability.get("excludes_categories", [])}
        if requested.upper() in excluded:
            return False

        applies_to = applicability.get("applies_to_categories")
        if applies_to:
            tokens = {item.upper() for item in applies_to}
            if "*" not in tokens and requested.upper() not in tokens:
                return False
            return True

    return matches_any_category(rule_category, applicability, {requested.upper()})


def matches_any_category(rule_category: str, applicability: dict[str, Any] | None, requested: set[str]) -> bool:
    requested_upper = {item.upper() for item in requested}

    if applicability:
        excluded = {item.upper() for item in applicability.get("excludes_categories", [])}
        if requested_upper & excluded:
            return False

        applies_to = applicability.get("applies_to_categories")
        if applies_to:
            tokens = {item.upper() for item in applies_to}
            if "*" in tokens:
                return True
            return bool(tokens & requested_upper)

    return bool(requested_upper & {rule_category.upper(), "PACKAGED_COMMODITY"})


def is_authoritative(rule_status: str, verification_status: str) -> bool:
    return rule_status == RuleStatus.ACTIVE and verification_status == VerificationStatus.VERIFIED
