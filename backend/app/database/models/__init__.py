"""Import every mapped class so Base.metadata and Alembic see the full schema."""

from app.database.models.declaration import Declaration
from app.database.models.evidence import Evidence
from app.database.models.ingredient import Ingredient
from app.database.models.inspection import Inspection
from app.database.models.legal_rule import LegalRule
from app.database.models.nutrition import NutritionData
from app.database.models.product import Product, ProductImage
from app.database.models.report import Report
from app.database.models.user import User
from app.database.models.violation import Violation

APPLICATION_TABLES = (
    "users",
    "products",
    "product_images",
    "inspections",
    "declarations",
    "nutrition_data",
    "ingredients",
    "legal_rules",
    "violations",
    "evidence",
    "reports",
)

__all__ = [
    "APPLICATION_TABLES",
    "Declaration",
    "Evidence",
    "Ingredient",
    "Inspection",
    "LegalRule",
    "NutritionData",
    "Product",
    "ProductImage",
    "Report",
    "User",
    "Violation",
]
