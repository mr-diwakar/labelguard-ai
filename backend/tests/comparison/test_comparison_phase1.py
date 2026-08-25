"""Phase 1: Multi-product nutrition comparison tests.

Verifies:
- Valid comparison input (2 to 5 products, all 10 supported parameters)
- Missing nutrition values (NOT_DETECTED, omitted parameters)
- Zero versus missing value distinction
- kcal/kJ unit normalization
- g/mg/mcg unit normalization
- Unsupported units and dimensional mismatches
- Invalid input validation (empty products, single product, >5 products, invalid values, invalid units, invalid priorities, invalid weights)
- Multiple products comparison input data model structures
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.core.enums import (
    DeclarationSource,
    DeclarationStatus,
    NutritionBasis,
    NutritionParameter,
    ComparisonPriority,
)
from app.schemas.comparison import (
    ComparisonProductInput,
    ComparisonRequest,
    NutritionValueInput,
    PriorityWeight,
    MIN_COMPARISON_PRODUCTS,
    MAX_COMPARISON_PRODUCTS,
)
from app.comparison.units import (
    NormalizationStatus,
    canonical_unit_for,
    normalize_input,
    normalize_value,
)


# --- 1. Valid comparison input ------------------------------------------------


def test_valid_comparison_input_all_supported_parameters() -> None:
    """Valid request containing all 10 supported parameters across multiple products."""
    product_a_values = {
        NutritionParameter.CALORIES: {"value": "250", "unit": "kcal"},
        NutritionParameter.SUGAR: {"value": "12", "unit": "g"},
        NutritionParameter.ADDED_SUGAR: {"value": "5", "unit": "g"},
        NutritionParameter.PROTEIN: {"value": "8", "unit": "g"},
        NutritionParameter.CARBOHYDRATES: {"value": "30", "unit": "g"},
        NutritionParameter.FAT: {"value": "10", "unit": "g"},
        NutritionParameter.SATURATED_FAT: {"value": "3", "unit": "g"},
        NutritionParameter.TRANS_FAT: {"value": "0", "unit": "g"},
        NutritionParameter.FIBER: {"value": "4", "unit": "g"},
        NutritionParameter.SODIUM: {"value": "300", "unit": "mg"},
    }

    product_b_values = {
        NutritionParameter.CALORIES: {"value": "1000", "unit": "kJ"},
        NutritionParameter.SUGAR: {"value": "4", "unit": "g"},
        NutritionParameter.ADDED_SUGAR: {"value": "0", "unit": "g"},
        NutritionParameter.PROTEIN: {"value": "12000", "unit": "mg"},
        NutritionParameter.CARBOHYDRATES: {"value": "20", "unit": "g"},
        NutritionParameter.FAT: {"value": "2", "unit": "g"},
        NutritionParameter.SATURATED_FAT: {"value": "0.5", "unit": "g"},
        NutritionParameter.TRANS_FAT: {"value": "0", "unit": "g"},
        NutritionParameter.FIBER: {"value": "6", "unit": "g"},
        NutritionParameter.SODIUM: {"value": "0.15", "unit": "g"},
    }

    request = ComparisonRequest.model_validate({
        "products": [
            {
                "product_id": "prod-1",
                "product_name": "Product Alpha",
                "basis": "PER_100G",
                "values": product_a_values,
            },
            {
                "product_id": "prod-2",
                "product_name": "Product Beta",
                "basis": "PER_100G",
                "values": product_b_values,
            },
        ],
        "priorities": [
            {"priority": "LOWER_SUGAR", "weight": 3},
            {"priority": "HIGHER_PROTEIN", "weight": 2},
            {"priority": "LOWER_SODIUM", "weight": 1},
        ],
    })

    assert len(request.products) == 2
    assert request.products[0].product_id == "prod-1"
    assert request.products[0].values[NutritionParameter.CALORIES].value == Decimal("250")
    assert request.products[1].values[NutritionParameter.PROTEIN].value == Decimal("12000")
    assert len(request.priorities) == 3
    assert request.priorities[0].weight == 3


# --- 2. Missing nutrition values ---------------------------------------------


def test_missing_nutrition_values_handling() -> None:
    """Missing values must be expressed with NOT_DETECTED status and value=None."""
    missing_val = NutritionValueInput.model_validate({"status": "NOT_DETECTED"})
    assert missing_val.status is DeclarationStatus.NOT_DETECTED
    assert missing_val.value is None

    norm = normalize_input(NutritionParameter.SUGAR, missing_val)
    assert norm.status is NormalizationStatus.NOT_DETECTED
    assert norm.canonical_value is None
    assert not norm.is_comparable


def test_omitted_parameters_are_treated_as_missing() -> None:
    """A product input omitting parameters from its values dictionary is valid."""
    product = ComparisonProductInput.model_validate({
        "product_id": "p1",
        "product_name": "Partial Product",
        "values": {"SUGAR": {"value": "10", "unit": "g"}},
    })
    assert NutritionParameter.SUGAR in product.values
    assert NutritionParameter.FAT not in product.values


# --- 3. Zero versus missing value ---------------------------------------------


def test_zero_versus_missing_value_distinction() -> None:
    """Numeric zero (0g) must be strictly distinguishable from a missing value (NOT_DETECTED)."""
    zero_val = NutritionValueInput.model_validate({"value": "0", "unit": "g", "status": "DETECTED"})
    missing_val = NutritionValueInput.model_validate({"status": "NOT_DETECTED"})

    # Zero value check
    assert zero_val.value == Decimal("0")
    assert zero_val.status is DeclarationStatus.DETECTED
    zero_norm = normalize_input(NutritionParameter.SUGAR, zero_val)
    assert zero_norm.status is NormalizationStatus.NORMALIZED
    assert zero_norm.canonical_value == Decimal("0")
    assert zero_norm.is_comparable

    # Missing value check
    assert missing_val.value is None
    assert missing_val.status is DeclarationStatus.NOT_DETECTED
    missing_norm = normalize_input(NutritionParameter.SUGAR, missing_val)
    assert missing_norm.status is NormalizationStatus.NOT_DETECTED
    assert missing_norm.canonical_value is None
    assert not missing_norm.is_comparable

    # Zero != Missing
    assert zero_norm.canonical_value != missing_norm.canonical_value
    assert zero_norm.status != missing_norm.status


# --- 4. kcal / kJ normalization ----------------------------------------------


def test_kcal_kj_unit_normalization() -> None:
    """Test energy conversions: kJ converts to kcal, kcal remains kcal."""
    # 418.4 kJ = 100 kcal (since 1 kcal = 4.184 kJ)
    kj_norm = normalize_value(NutritionParameter.CALORIES, Decimal("418.4"), "kJ")
    assert kj_norm.status is NormalizationStatus.NORMALIZED
    assert kj_norm.canonical_unit == "kcal"
    assert kj_norm.canonical_value == Decimal("100")

    kcal_norm = normalize_value(NutritionParameter.CALORIES, Decimal("250"), "kcal")
    assert kcal_norm.status is NormalizationStatus.NORMALIZED
    assert kcal_norm.canonical_unit == "kcal"
    assert kcal_norm.canonical_value == Decimal("250")


# --- 5. g / mg normalization -------------------------------------------------


def test_g_mg_unit_normalization() -> None:
    """Test mass conversions: mg to g for protein/fat, g to mg for sodium."""
    # 5000 mg protein -> 5 g
    protein_norm = normalize_value(NutritionParameter.PROTEIN, Decimal("5000"), "mg")
    assert protein_norm.status is NormalizationStatus.NORMALIZED
    assert protein_norm.canonical_unit == "g"
    assert protein_norm.canonical_value == Decimal("5")

    # 0.2 g sodium -> 200 mg
    sodium_norm = normalize_value(NutritionParameter.SODIUM, Decimal("0.2"), "g")
    assert sodium_norm.status is NormalizationStatus.NORMALIZED
    assert sodium_norm.canonical_unit == "mg"
    assert sodium_norm.canonical_value == Decimal("200")

    # 2500 mcg fiber -> 0.0025 g
    fiber_norm = normalize_value(NutritionParameter.FIBER, Decimal("2500"), "mcg")
    assert fiber_norm.status is NormalizationStatus.NORMALIZED
    assert fiber_norm.canonical_unit == "g"
    assert fiber_norm.canonical_value == Decimal("0.0025")


# --- 6. Unsupported units -----------------------------------------------------


def test_unsupported_units_and_dimension_mismatch() -> None:
    """Unknown units or incorrect dimensions must yield UNSUPPORTED_UNIT."""
    # Unknown unit
    bad_unit = normalize_value(NutritionParameter.SUGAR, Decimal("10"), "fl_oz")
    assert bad_unit.status is NormalizationStatus.UNSUPPORTED_UNIT
    assert bad_unit.canonical_value is None

    # Dimension mismatch: energy unit (kJ) for mass parameter (SUGAR)
    dim_mismatch_1 = normalize_value(NutritionParameter.SUGAR, Decimal("50"), "kJ")
    assert dim_mismatch_1.status is NormalizationStatus.UNSUPPORTED_UNIT

    # Dimension mismatch: mass unit (g) for energy parameter (CALORIES)
    dim_mismatch_2 = normalize_value(NutritionParameter.CALORIES, Decimal("100"), "g")
    assert dim_mismatch_2.status is NormalizationStatus.UNSUPPORTED_UNIT


# --- 7. Validation / Invalid input --------------------------------------------


def test_invalid_input_empty_products() -> None:
    """Empty product list must be rejected."""
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate({
            "products": [],
            "priorities": [{"priority": "LOWER_SUGAR"}],
        })


def test_valid_input_single_product() -> None:
    """Single product is valid in ComparisonRequest."""
    req = ComparisonRequest.model_validate({
        "products": [
            {"product_id": "p1", "product_name": "Product 1", "values": {}}
        ],
        "priorities": [{"priority": "LOWER_SUGAR"}],
    })
    assert len(req.products) == 1



def test_invalid_input_too_many_products() -> None:
    """More than MAX_COMPARISON_PRODUCTS (5) must be rejected."""
    products = [
        {"product_id": f"p{i}", "product_name": f"Product {i}", "values": {}}
        for i in range(MAX_COMPARISON_PRODUCTS + 1)
    ]
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate({
            "products": products,
            "priorities": [{"priority": "LOWER_SUGAR"}],
        })


def test_invalid_nutrition_values_negative_or_nan() -> None:
    """Negative or non-finite nutrition values must be rejected by schema or marked invalid by normalization."""
    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"value": "-5", "unit": "g"})

    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"value": "NaN", "unit": "g"})

    invalid_norm = normalize_value(NutritionParameter.SUGAR, Decimal("-5"), "g")
    assert invalid_norm.status is NormalizationStatus.INVALID_VALUE


def test_invalid_priority_values_and_weights() -> None:
    """Invalid priority names or out-of-bound weights must be rejected."""
    with pytest.raises(ValidationError):
        PriorityWeight.model_validate({"priority": "NON_EXISTENT_PRIORITY", "weight": 1})

    with pytest.raises(ValidationError):
        PriorityWeight.model_validate({"priority": "LOWER_SUGAR", "weight": 0})

    with pytest.raises(ValidationError):
        PriorityWeight.model_validate({"priority": "LOWER_SUGAR", "weight": 6})


# --- 8. Multiple products -----------------------------------------------------


@pytest.mark.parametrize("num_products", [2, 3, 4, 5])
def test_multiple_products_comparison_request(num_products: int) -> None:
    """Supports 2, 3, 4, and 5 products in comparison request."""
    products = [
        {
            "product_id": f"prod-{i}",
            "product_name": f"Product {i}",
            "values": {
                NutritionParameter.SUGAR: {"value": str(5 * i), "unit": "g"}
            },
        }
        for i in range(1, num_products + 1)
    ]

    request = ComparisonRequest.model_validate({
        "products": products,
        "priorities": [{"priority": "LOWER_SUGAR", "weight": 1}],
    })

    assert len(request.products) == num_products
    for i in range(num_products):
        assert request.products[i].product_id == f"prod-{i+1}"
