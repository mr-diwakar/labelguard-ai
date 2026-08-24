"""
Select the rule version that was in force on the inspection date, then classify it.

This module does not validate declarations and does not produce COMPLIANT / POTENTIAL_NON_COMPLIANCE.
"""

from collections import defaultdict

from app.compliance.applicability import (
    context_category_tokens,
    is_authoritative,
    is_effective_on,
    matches_any_category,
)
from app.compliance.dates import as_inspection_date
from app.core.enums import ApplicabilityDecision, RuleStatus
from app.schemas.applicability import ApplicabilityReport, ProductContext, RuleApplicability
from app.schemas.legal_rule import LegalRuleRecord


def versions_in_force(versions: list[LegalRuleRecord], inspection_date) -> list[LegalRuleRecord]:
    on_date = as_inspection_date(inspection_date)
    return [
        version
        for version in versions
        if is_effective_on(version.effective_from, version.effective_to, on_date)
    ]


def select_version_for_date(versions: list[LegalRuleRecord], inspection_date) -> LegalRuleRecord | None:
    """
    Returns the single version in force on inspection_date.

    Overlapping windows are not resolved here. The caller must treat that as a conflict.
    """
    in_force = versions_in_force(versions, inspection_date)
    if len(in_force) != 1:
        return None
    return in_force[0]


def evaluate_applicability(rules: list[LegalRuleRecord], context: ProductContext) -> ApplicabilityReport:
    on_date = as_inspection_date(context.inspection_date)
    category = str(context.category)
    tokens = context_category_tokens(category, context.is_imported)

    grouped: dict[str, list[LegalRuleRecord]] = defaultdict(list)
    for rule in rules:
        grouped[rule.rule_code].append(rule)

    report = ApplicabilityReport(inspection_date=on_date, category=category)

    for rule_code, versions in grouped.items():
        in_force = versions_in_force(versions, on_date)
        if len(in_force) > 1:
            _bucket(report, _overlap(in_force, on_date))
            continue
        if not in_force:
            _bucket(report, _out_of_window(versions, on_date))
            continue

        _bucket(report, _classify_in_force(in_force[0], tokens, context))

    return report


def _overlap(in_force: list[LegalRuleRecord], on_date) -> RuleApplicability:
    ordered = sorted(in_force, key=lambda item: (item.effective_from, item.source_version))
    windows = ", ".join(
        f"{item.source_version} ({item.effective_from.isoformat()}–{item.effective_to.isoformat() if item.effective_to else 'open'})"
        for item in ordered
    )
    return RuleApplicability(
        decision=ApplicabilityDecision.OVERLAP,
        reason=(
            f"Overlapping versions of {ordered[0].rule_code} are in force on {on_date.isoformat()}: "
            f"{windows}. The resolver will not silently pick one."
        ),
        rule=ordered[0],
        selected_version=ordered[0].source_version,
    )


def _out_of_window(versions: list[LegalRuleRecord], on_date) -> RuleApplicability:
    newest = sorted(versions, key=lambda item: item.effective_from)[-1]
    earliest = sorted(versions, key=lambda item: item.effective_from)[0]

    if on_date < earliest.effective_from:
        return RuleApplicability(
            decision=ApplicabilityDecision.FUTURE,
            reason=f"No version of {newest.rule_code} is in force before {earliest.effective_from.isoformat()}.",
            rule=newest,
            selected_version=newest.source_version,
        )

    return RuleApplicability(
        decision=ApplicabilityDecision.EXPIRED,
        reason=f"No version of {newest.rule_code} is in force on {on_date.isoformat()}.",
        rule=newest,
        selected_version=newest.source_version,
    )


def _classify_in_force(
    rule: LegalRuleRecord,
    tokens: set[str],
    context: ProductContext,
) -> RuleApplicability:
    if not matches_any_category(rule.category, rule.applicability_condition, tokens):
        return RuleApplicability(
            decision=ApplicabilityDecision.NOT_APPLICABLE,
            reason="The product category is outside this rule version's recorded applicability.",
            rule=rule,
            selected_version=rule.source_version,
        )

    condition = (rule.applicability_condition or {}).get("condition")
    if condition == "ONLY_WHEN_SIZE_IS_RELEVANT" and context.size_is_relevant is not True:
        return RuleApplicability(
            decision=ApplicabilityDecision.NOT_APPLICABLE,
            reason="Rule 6(1)(f) applies only when the sizes of the commodity are relevant.",
            rule=rule,
            selected_version=rule.source_version,
        )

    if rule.rule_status == RuleStatus.DRAFT or not is_authoritative(rule.rule_status, rule.verification_status):
        return RuleApplicability(
            decision=ApplicabilityDecision.UNVERIFIED,
            reason="This version is in scope but is not ACTIVE and VERIFIED, so it is not used as production law.",
            rule=rule,
            selected_version=rule.source_version,
        )

    return RuleApplicability(
        decision=ApplicabilityDecision.APPLICABLE,
        reason="This verified version is in force and matches the product context.",
        rule=rule,
        selected_version=rule.source_version,
    )


def _bucket(report: ApplicabilityReport, item: RuleApplicability) -> None:
    {
        ApplicabilityDecision.APPLICABLE: report.applicable,
        ApplicabilityDecision.NOT_APPLICABLE: report.not_applicable,
        ApplicabilityDecision.EXPIRED: report.expired,
        ApplicabilityDecision.FUTURE: report.future,
        ApplicabilityDecision.UNVERIFIED: report.unverified,
        ApplicabilityDecision.OVERLAP: report.overlaps,
    }[item.decision].append(item)
