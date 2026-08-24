"""
Inspection context contract (Phase 11).

Wraps the engine's existing selection facts (ProductContext / ComplianceRequest) and
adds the surrounding metadata a scan carries: inspection id, source, product
identifier and the rule-version context. It does not replace the engine input; it
builds it. inspection_datetime is what drives historical rule selection, so a 2024
inspection keeps using 2024 rules (Phase 10 reproducibility).
"""

from collections.abc import Sequence
from datetime import date, datetime

from pydantic import Field

from app.core.enums import ProductCategory
from app.schemas.applicability import ProductContext
from app.schemas.assessment import ComplianceRequest
from app.schemas.common import APIModel
from app.schemas.contracts.detection import ExtractedDeclaration
from app.schemas.declaration import Declaration


class InspectionContext(APIModel):
    """
    Context in which one assessment is performed.

    Example:
        {
            "inspection_id": "insp_2026_0001",
            "inspection_datetime": "2026-08-24T10:15:00Z",
            "product_category": "PACKAGED_FOOD",
            "product_identifier": "8901234567890",
            "source": "MOBILE_SCAN",
            "rule_version_context": "2011-baseline",
            "label_readable": true
        }
    """

    inspection_id: str | None = None
    inspection_datetime: date | datetime
    product_category: ProductCategory | str
    product_identifier: str | None = None
    source: str | None = None
    # Records which rule corpus/version was in force for this inspection. The engine
    # still selects rules by inspection_datetime; this is metadata for reproducibility.
    rule_version_context: str | None = None
    is_imported: bool = False
    size_is_relevant: bool | None = None
    label_readable: bool | None = None

    def to_product_context(self) -> ProductContext:
        """Facts the RuleResolver needs. Nothing else leaks into rule selection."""
        return ProductContext(
            inspection_date=self.inspection_datetime,
            category=self.product_category,
            is_imported=self.is_imported,
            size_is_relevant=self.size_is_relevant,
        )

    def to_compliance_request(
        self,
        declarations: Sequence[Declaration | ExtractedDeclaration] | None = None,
    ) -> ComplianceRequest:
        """
        Build the existing engine input. ExtractedDeclaration items are adapted to
        the legal Declaration vocabulary; NOT_APPLICABLE items are dropped (they are
        not evidence for the engine). Declared-Declaration items pass through as-is.
        """
        legal: list[Declaration] = []
        for item in declarations or []:
            if isinstance(item, ExtractedDeclaration):
                adapted = item.to_declaration(label_readable=self.label_readable)
                if adapted is not None:
                    legal.append(adapted)
            else:
                legal.append(item)

        return ComplianceRequest(
            inspection_date=self.inspection_datetime,
            product_category=self.product_category,
            is_imported=self.is_imported,
            size_is_relevant=self.size_is_relevant,
            label_readable=self.label_readable,
            declarations=legal,
        )
