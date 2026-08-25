"""Phase 13: multi-product comparison contracts parse valid input and reject invalid input.

These cover only the data models. Scoring, normalisation and ranking arrive in a later phase.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.enums import (
    ComparisonOutcome,
    ComparisonStatus,
    DeclarationSource,
    DeclarationStatus,
    NutritionBasis,
    NutritionParameter,
    ParameterDirection,
)
from app.schemas.comparison import (
    DISCLAIMER,
    MAX_COMPARISON_PRODUCTS,
    ComparisonProductInput,
    ComparisonRequest,
    ComparisonResult,
    NutritionValueInput,
    ParameterScore,
    PriorityWeight,
)


def _request_payload(**overrides) -> dict:
    payload = {
        "products": [
            {
                "product_id": "A",
                "product_name": "Brand A",
                "values": {
                    "SUGAR": {"value": "10", "unit": "g"},
                    "PROTEIN": {"value": "8", "unit": "g"},
                },
            },
            {
                "product_id": "B",
                "product_name": "Brand B",
                "values": {
                    "SUGAR": {"value": "5", "unit": "g"},
                    "PROTEIN": {"status": "NOT_DETECTED"},
                },
            },
        ],
        "priorities": [
            {"priority": "LOWER_SUGAR", "weight": 2},
            {"priority": "HIGHER_PROTEIN"},
        ],
    }
    payload.update(overrides)
    return payload


# --- valid input -------------------------------------------------------------


def test_valid_request_parses_and_reuses_declaration_status() -> None:
    request = ComparisonRequest.model_validate(_request_payload())

    a, b = request.products
    assert a.basis is NutritionBasis.PER_100G  # default basis
    assert a.values[NutritionParameter.SUGAR].value == Decimal("10")
    assert a.values[NutritionParameter.SUGAR].status is DeclarationStatus.DETECTED
    assert b.values[NutritionParameter.PROTEIN].status is DeclarationStatus.NOT_DETECTED
    assert b.values[NutritionParameter.PROTEIN].value is None
    assert request.priorities[1].weight == 1  # optional weight defaults to 1


def test_missing_parameter_may_be_omitted_entirely() -> None:
    payload = _request_payload()
    payload["products"][0]["values"] = {}  # nothing extracted for product A
    request = ComparisonRequest.model_validate(payload)

    assert request.products[0].values == {}


def test_value_accepts_decimal_and_source_defaults_to_ocr() -> None:
    value = NutritionValueInput.model_validate({"value": Decimal("1.5"), "unit": "g"})

    assert value.source is DeclarationSource.OCR
    assert value.confidence is None


def test_low_confidence_value_is_allowed() -> None:
    value = NutritionValueInput.model_validate(
        {"value": "5", "unit": "g", "status": "LOW_CONFIDENCE", "confidence": 0.4}
    )

    assert value.status is DeclarationStatus.LOW_CONFIDENCE


def test_blank_unit_is_normalised_to_none() -> None:
    value = NutritionValueInput.model_validate({"value": "5", "unit": "  "})

    assert value.unit is None


# --- product-list validation -------------------------------------------------


def test_empty_product_list_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate(_request_payload(products=[]))


def test_single_product_is_accepted() -> None:
    payload = _request_payload()
    payload["products"] = [payload["products"][0]]
    req = ComparisonRequest.model_validate(payload)
    assert len(req.products) == 1



def test_too_many_products_is_rejected() -> None:
    products = [
        {"product_id": f"P{i}", "product_name": f"Brand {i}", "values": {"SUGAR": {"value": "1", "unit": "g"}}}
        for i in range(MAX_COMPARISON_PRODUCTS + 1)
    ]
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate(_request_payload(products=products))


def test_duplicate_product_id_is_rejected() -> None:
    payload = _request_payload()
    payload["products"][1]["product_id"] = "A"
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate(payload)


def test_blank_product_identifier_is_rejected() -> None:
    payload = _request_payload()
    payload["products"][0]["product_id"] = "   "
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate(payload)


def test_empty_product_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ComparisonProductInput.model_validate({"product_id": "A", "product_name": ""})


# --- parameter validation ----------------------------------------------------


def test_unknown_parameter_key_is_rejected() -> None:
    payload = _request_payload()
    payload["products"][0]["values"]["VITAMIN_C"] = {"value": "1", "unit": "mg"}
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate(payload)


# --- nutrition value validation ----------------------------------------------


def test_negative_nutrition_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"value": "-1", "unit": "g"})


def test_non_finite_nutrition_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"value": "Infinity", "unit": "g"})
    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"value": "NaN", "unit": "g"})


def test_value_with_embedded_unit_is_rejected() -> None:
    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"value": "10 g"})


def test_detected_value_requires_a_magnitude() -> None:
    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"status": "DETECTED"})


def test_not_detected_value_must_not_carry_a_magnitude() -> None:
    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"status": "NOT_DETECTED", "value": "5", "unit": "g"})


def test_missing_value_is_represented_as_not_detected_never_zero() -> None:
    value = NutritionValueInput.model_validate({"status": "NOT_DETECTED"})

    assert value.value is None
    assert value.status is DeclarationStatus.NOT_DETECTED


def test_confidence_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        NutritionValueInput.model_validate({"value": "5", "unit": "g", "confidence": 1.5})


# --- weight and priority validation ------------------------------------------


def test_weight_below_one_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PriorityWeight.model_validate({"priority": "LOWER_SUGAR", "weight": 0})


def test_weight_above_five_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PriorityWeight.model_validate({"priority": "LOWER_SUGAR", "weight": 6})


def test_invalid_priority_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PriorityWeight.model_validate({"priority": "HIGHER_SUGAR"})  # not a real priority


def test_empty_priorities_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate(_request_payload(priorities=[]))


def test_duplicate_priority_is_rejected() -> None:
    payload = _request_payload(
        priorities=[
            {"priority": "LOWER_SUGAR", "weight": 2},
            {"priority": "LOWER_SUGAR", "weight": 1},
        ]
    )
    with pytest.raises(ValidationError):
        ComparisonRequest.model_validate(payload)


def test_models_forbid_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        PriorityWeight.model_validate({"priority": "LOWER_SUGAR", "weight": 1, "extra": True})


# --- result contracts --------------------------------------------------------


def test_result_schemas_build_and_carry_default_disclaimer() -> None:
    result = ComparisonResult.model_validate(
        {
            "status": "COMPLETED",
            "ranking": [{"rank": 1, "product_id": "B", "product_name": "Brand B", "score": 0.9}],
            "products": [
                {
                    "product_id": "B",
                    "product_name": "Brand B",
                    "rank": 1,
                    "score": 0.9,
                    "outcome": "RANKED",
                    "coverage": 1.0,
                    "parameter_scores": [
                        {
                            "parameter": "SUGAR",
                            "direction": "LOWER_BETTER",
                            "canonical_value": "5",
                            "unit": "g",
                            "status": "DETECTED",
                            "included": True,
                            "normalized_score": 1.0,
                            "weight": 2,
                            "weighted_contribution": 0.66,
                            "note": "Lowest sugar of the compared products.",
                        }
                    ],
                    "highlights": ["Lowest sugar"],
                }
            ],
            "active_parameters": ["SUGAR", "PROTEIN"],
            "excluded_parameters": [
                {"parameter": "PROTEIN", "reason": "Declared by fewer than two products."}
            ],
            "priorities_used": [{"priority": "LOWER_SUGAR", "weight": 2}],
            "explanation": "Brand B ranks highest for your selected priorities.",
        }
    )

    assert result.status is ComparisonStatus.COMPLETED
    assert result.disclaimer == DISCLAIMER  # supplied by default, not by the caller
    assert result.products[0].outcome is ComparisonOutcome.RANKED
    assert result.products[0].parameter_scores[0].direction is ParameterDirection.LOWER_BETTER
    assert result.ranking[0].rank == 1
    assert result.excluded_parameters[0].parameter is NutritionParameter.PROTEIN


def test_normalized_score_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ParameterScore.model_validate(
            {
                "parameter": "SUGAR",
                "direction": "LOWER_BETTER",
                "status": "DETECTED",
                "normalized_score": 1.5,
            }
        )
