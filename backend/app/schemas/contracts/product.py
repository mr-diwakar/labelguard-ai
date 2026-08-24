"""
Product profile contract (Phase 11).

A product as understood from a scan, BEFORE anything is persisted. The existing
ProductResponse requires a database UUID; a scan in progress has no row yet, so this
carries the same descriptive facts with every field optional and no id. A persistence
layer can later map an accepted ProductProfile onto a Product row — that mapping is not
implemented here.
"""

from app.core.enums import ProductCategory
from app.schemas.common import APIModel


class ProductProfile(APIModel):
    """
    Example:
        {
            "name": "Whole Wheat Biscuits",
            "brand": "Acme",
            "category": "PACKAGED_FOOD",
            "net_quantity": "500 g",
            "mrp": "50",
            "barcode": "8901234567890"
        }

    category accepts an unknown string as well as ProductCategory so an unrecognised
    label category degrades to review rather than a validation crash.
    """

    name: str | None = None
    brand: str | None = None
    category: ProductCategory | str | None = None
    net_quantity: str | None = None
    mrp: str | None = None
    barcode: str | None = None
    product_identifier: str | None = None
