"""
Orchestration for multi-product nutrition comparison.

This is the module's public entry point. It consumes *already-extracted*
nutrition (it never performs OCR or nutrition extraction), scores products
deterministically, and returns an explainable ``ComparisonResult``.

Pipeline:
    validate -> normalise units -> score/rank -> explain -> assemble

The adapter helpers at the bottom bridge Teammate 2's ``NutritionResult``
contract into ``ProductNutritionInput`` without this module knowing anything
about OCR internals.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app.nutrition.comparison.explanation import build_highlights, headline
from app.nutrition.comparison.parameters import canonical_unit, display_name, resolve_parameter
from app.nutrition.comparison.schema import (
    ComparisonRequest,
    ComparisonResult,
    CriterionSummary,
    NutrientValueInput,
    ParameterCell,
    ProductNutritionInput,
    ProductRanking,
)
from app.nutrition.comparison.scoring import (
    ParameterScoring,
    ProductScore,
    ScoreBoard,
    build_scoreboard,
    resolve_priorities,
)
from app.nutrition.comparison.scoring_normalization import NormalizedTable, build_normalized_table
from app.nutrition.comparison.units import NormalizationStatus


def compare(request: ComparisonRequest) -> ComparisonResult:
    """Compare products by the consumer's selected priorities.

    Pure function of the request: same input always yields the same result.
    Raises ``ValueError`` only for structurally invalid input (e.g. duplicate
    product ids); "soft" problems (unknown nutrients, missing data, no
    priorities) are reported via ``warnings`` rather than raised.
    """

    if request is None:  # defensive: callers sometimes forward Optional
        raise ValueError("A ComparisonRequest is required.")

    products = request.products
    if not products:
        message = "No products were provided to compare."
        return ComparisonResult(warnings=[message], explanation=[message])

    _ensure_unique_ids(products)

    product_ids = [product.product_id for product in products]
    name_by_id = {p.product_id: (p.display_name or p.product_id) for p in products}

    table, warnings = build_normalized_table(products)
    resolved = resolve_priorities(request.priorities)

    if not resolved:
        warnings.append(
            "No comparison priorities were selected, so products were listed without scoring."
        )
    if len(products) < 2:
        warnings.append(
            "Only one product was provided; there is nothing to compare it against."
        )

    board = build_scoreboard(product_ids, resolved, table)

    cells_by_product = {
        pid: _cells_for_product(pid, board.parameters, table) for pid in product_ids
    }
    highlights_by_product = {
        pid: build_highlights(pid, board.parameters, name_by_id) for pid in product_ids
    }

    rankings = _build_rankings(board, name_by_id, cells_by_product, highlights_by_product)
    criteria = [_criterion(scoring) for scoring in board.parameters]

    scored = [p for p in board.products if p.score is not None]
    winner_id = scored[0].product_id if scored else None
    winner_name = name_by_id.get(winner_id) if winner_id else None

    explanation = _build_explanation(
        board=board,
        scored=scored,
        resolved_count=len(resolved),
        product_count=len(products),
        name_by_id=name_by_id,
        winner_highlights=highlights_by_product.get(winner_id, []) if winner_id else [],
    )

    if winner_id is not None:
        winner_score = scored[0]
        if winner_score.not_detected_parameters:
            missing = ", ".join(display_name(p) for p in winner_score.not_detected_parameters)
            warnings.append(
                f"The top-ranked product had no data for: {missing}. It was scored only on the "
                f"parameters it did have."
            )

    return ComparisonResult(
        rankings=rankings,
        winner=winner_id,
        winner_display_name=winner_name,
        criteria=criteria,
        explanation=explanation,
        warnings=warnings,
        tie=board.tie,
    )


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


def _ensure_unique_ids(products: Sequence[ProductNutritionInput]) -> None:
    seen: set[str] = set()
    for product in products:
        if product.product_id in seen:
            raise ValueError(
                f"Duplicate product_id '{product.product_id}'. Each product being compared "
                f"must have a unique id."
            )
        seen.add(product.product_id)


# --------------------------------------------------------------------------- #
# Presentation helpers
# --------------------------------------------------------------------------- #


def _fmt_number(value: float) -> str:
    """Render a canonical value without scientific notation or trailing zeros."""

    decimal = Decimal(str(value)).normalize()
    return format(decimal, "f")


def _cells_for_product(
    product_id: str,
    scorings: list[ParameterScoring],
    table: NormalizedTable,
) -> list[ParameterCell]:
    cells: list[ParameterCell] = []
    for scoring in scorings:
        parameter = scoring.parameter
        normalized = table.get(product_id, {}).get(parameter)
        status = normalized.status if normalized is not None else NormalizationStatus.NOT_DETECTED

        value: float | None = None
        unit: str | None = None
        note: str | None = None

        if status is NormalizationStatus.OK and normalized is not None:
            value = normalized.value
            unit = canonical_unit(parameter)
            display = f"{_fmt_number(value)} {unit}".strip()
            available = True
            if not scoring.differentiating:
                note = scoring.note
        else:
            available = False
            if status is NormalizationStatus.NOT_DETECTED:
                display = "NOT_DETECTED"
            else:
                display = "UNAVAILABLE"
            if status is NormalizationStatus.UNRECOGNIZED_UNIT:
                note = (
                    f"Unit '{normalized.raw_unit if normalized else ''}' was not recognised, "
                    f"so this value was excluded from scoring."
                )
            elif status is NormalizationStatus.INVALID_VALUE:
                note = "Value could not be read as a non-negative number, so it was excluded."

        cells.append(
            ParameterCell(
                parameter=parameter,
                available=available,
                value=value,
                unit=unit,
                display=display,
                sub_score=scoring.sub_scores.get(product_id) if scoring.differentiating else None,
                note=note,
            )
        )
    return cells


def _assign_ranks(products: list[ProductScore]) -> dict[str, int]:
    """Standard competition ranking: equal (score, coverage) share a rank."""

    ranks: dict[str, int] = {}
    prev_key: tuple[float | None, float] | None = None
    prev_rank = 0
    for index, product in enumerate(products):
        key = (product.score, round(product.coverage, 6))
        if prev_key is not None and key == prev_key:
            ranks[product.product_id] = prev_rank
        else:
            prev_rank = index + 1
            ranks[product.product_id] = prev_rank
            prev_key = key
    return ranks


def _build_rankings(
    board: ScoreBoard,
    name_by_id: dict[str, str],
    cells_by_product: dict[str, list[ParameterCell]],
    highlights_by_product: dict[str, list[str]],
) -> list[ProductRanking]:
    ranks = _assign_ranks(board.products)
    rankings: list[ProductRanking] = []
    for product in board.products:
        rankings.append(
            ProductRanking(
                rank=ranks[product.product_id],
                product_id=product.product_id,
                display_name=name_by_id[product.product_id],
                score=product.score,
                coverage=round(product.coverage, 6),
                scored_parameters=product.scored_parameters,
                not_detected_parameters=product.not_detected_parameters,
                cells=cells_by_product[product.product_id],
                highlights=highlights_by_product[product.product_id],
            )
        )
    return rankings


def _criterion(scoring: ParameterScoring) -> CriterionSummary:
    return CriterionSummary(
        parameter=scoring.parameter,
        direction=scoring.direction,
        weight=round(scoring.weight, 6),
        display_name=display_name(scoring.parameter),
        differentiating=scoring.differentiating,
        participating_products=len(scoring.participating_product_ids),
        note=scoring.note,
        best_product_id=scoring.best_product_id,
        not_detected_product_ids=scoring.not_detected_product_ids,
    )


def _join_names(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _build_explanation(
    board: ScoreBoard,
    scored: list[ProductScore],
    resolved_count: int,
    product_count: int,
    name_by_id: dict[str, str],
    winner_highlights: list[str],
) -> list[str]:
    if not scored:
        if board.tie:
            # Comparable across the selected parameters, but every compared value
            # was equal. This is a tie, not an "incomparable" result.
            tied_names = [name_by_id[p.product_id] for p in board.products]
            return [
                f"{_join_names(tied_names)} are tied on your selected parameters — their "
                f"compared values are equal."
            ]
        if resolved_count == 0:
            return ["No comparison parameters were selected, so the products are listed without a ranking."]
        if product_count < 2:
            return ["Only one product was provided, so there is nothing to compare it against."]
        return [
            "None of the selected parameters had comparable data across these products, "
            "so no ranking could be produced."
        ]

    lines: list[str] = []
    if board.tie:
        top = scored[0]
        tied_names = [
            name_by_id[p.product_id]
            for p in scored
            if p.score == top.score and round(p.coverage, 6) == round(top.coverage, 6)
        ]
        lines.append(
            f"{_join_names(tied_names)} are tied for the top rank based on your selected parameters."
        )
    else:
        lines.append(headline(name_by_id[scored[0].product_id]))

    lines.extend(winner_highlights)
    return lines


# --------------------------------------------------------------------------- #
# Adapters — bridge already-extracted data into ProductNutritionInput.
#
# These are the ONLY place that knows the external payload shape. If Teammate
# 2's NutritionResult.payload shape differs from the flat {nutrient: value} /
# {nutrient: {value, unit}} assumption below, only these functions change.
# --------------------------------------------------------------------------- #

_VALUE_KEYS = ("value", "amount", "quantity")
_UNIT_KEYS = ("unit", "units", "uom")


def _coerce_reading(raw: object) -> NutrientValueInput | float | str | None:
    """Turn one payload entry into something the schema accepts.

    A mapping is read for value/unit (extra keys like confidence are dropped so
    they don't trip ``extra='forbid'``); scalars pass through untouched.
    """

    if isinstance(raw, dict):
        value = next((raw[k] for k in _VALUE_KEYS if k in raw), None)
        unit = next((raw[k] for k in _UNIT_KEYS if k in raw), None)
        return NutrientValueInput(
            value=value if isinstance(value, (int, float)) or value is None else _maybe_float(value),
            unit=str(unit) if unit is not None else None,
        )
    if isinstance(raw, (int, float, str)) or raw is None:
        return raw  # type: ignore[return-value]
    return None


def _maybe_float(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def product_from_payload(
    product_id: str,
    payload: dict | None,
    display_name: str | None = None,
) -> ProductNutritionInput:
    """Build a ``ProductNutritionInput`` from a flat extraction payload.

    Only keys that resolve to a supported comparison parameter are kept; other
    fields (serving size, etc.) are ignored so they do not generate warnings.
    """

    nutrients: dict[str, NutrientValueInput | float | str | None] = {}
    for raw_key, raw_value in (payload or {}).items():
        if resolve_parameter(raw_key) is None:
            continue
        nutrients[raw_key] = _coerce_reading(raw_value)
    return ProductNutritionInput(
        product_id=product_id,
        display_name=display_name,
        nutrients=nutrients,
    )


def product_from_nutrition_result(
    product_id: str,
    result: object,
    display_name: str | None = None,
) -> ProductNutritionInput | None:
    """Adapt Teammate 2's ``NutritionResult`` into a comparison input.

    Returns ``None`` when the result is unavailable (``available`` is False or
    there is no payload), so the caller can decide whether to skip the product
    or surface "nutrition not available" to the consumer. Accepts either the
    Pydantic model or a plain object exposing ``available``/``payload``.
    """

    available = getattr(result, "available", False)
    payload = getattr(result, "payload", None)
    if not available or not payload:
        return None
    return product_from_payload(product_id, payload, display_name=display_name)
