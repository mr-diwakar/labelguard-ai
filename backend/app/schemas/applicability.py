from datetime import date, datetime

from pydantic import Field

from app.core.enums import ApplicabilityDecision, ProductCategory
from app.schemas.common import APIModel
from app.schemas.legal_rule import LegalRuleRecord


class ProductContext(APIModel):
    """
    Facts known at inspection time. Used only to select rules.

    is_imported is a product fact, not a legal conclusion. When True, IMPORTED_PRODUCT
    rules may be considered alongside the stated category.
    """

    inspection_date: date | datetime
    category: ProductCategory | str
    is_imported: bool = False
    size_is_relevant: bool | None = None


class RuleApplicability(APIModel):
    decision: ApplicabilityDecision
    reason: str
    rule: LegalRuleRecord
    selected_version: str


class ApplicabilityReport(APIModel):
    """Input the future compliance engine will consume. No PASS/FAIL lives here."""

    inspection_date: date
    category: str
    applicable: list[RuleApplicability] = Field(default_factory=list)
    not_applicable: list[RuleApplicability] = Field(default_factory=list)
    expired: list[RuleApplicability] = Field(default_factory=list)
    future: list[RuleApplicability] = Field(default_factory=list)
    unverified: list[RuleApplicability] = Field(default_factory=list)
    overlaps: list[RuleApplicability] = Field(default_factory=list)

    def codes(self, decision: ApplicabilityDecision) -> list[str]:
        bucket = {
            ApplicabilityDecision.APPLICABLE: self.applicable,
            ApplicabilityDecision.NOT_APPLICABLE: self.not_applicable,
            ApplicabilityDecision.EXPIRED: self.expired,
            ApplicabilityDecision.FUTURE: self.future,
            ApplicabilityDecision.UNVERIFIED: self.unverified,
            ApplicabilityDecision.OVERLAP: self.overlaps,
        }[decision]
        return [item.rule.rule_code for item in bucket]
