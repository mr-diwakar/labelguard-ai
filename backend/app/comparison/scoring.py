"""Deterministic, LLM-free scoring for the multi-product nutrition comparison (Phase 13 / Phase 3).

Pipeline (each stage is pure and explainable):

    raw values -> unit normalisation -> per-parameter normalisation -> user weights
               -> weighted score -> ranking -> explanation & trade-offs

Parameter direction (verified against the approved architecture; the ``LOWER_``/``HIGHER_``
prefix on :class:`ComparisonPriority` is the source of truth, mirrored in ``PRIORITY_SPEC``):

    LOWER_BETTER  : calories, sugar, added sugar, carbohydrates, fat, saturated fat,
                    trans fat, sodium
    HIGHER_BETTER : protein, fiber

Per-parameter normalisation -- relative min-max among the products that declare a comparable
value for that parameter (no fixed health thresholds; the repository defines none)::

    higher-is-better:  score = (value - min) / (max - min)
    lower-is-better:   score = (max - value) / (max - min)

When ``max == min`` (every comparable value is equal) the parameter cannot differentiate the
products, so each receives ``0.5`` -- a neutral score that neither rewards nor penalises.

Weighting and the final score, computed per product over only its *available* active
parameters (``A``)::

    effective_weight(p)      = raw_weight(p) / sum(raw_weight(q) for q in A)   # sums to 1
    weighted_contribution(p) = normalized_score(p) * effective_weight(p)
    final_score              = sum(weighted_contribution(p) for p in A)

Missing values are never invented and never zero: a parameter with no comparable value for a
product is dropped from that product's ``A`` (its remaining weights are re-normalised so they
still sum to 1). The product is therefore neither rewarded (no artificial best) nor penalised
(no artificial worst); its missingness is exposed via ``missing_parameters`` and ``coverage``.

A parameter that is comparable for fewer than two products is excluded from the whole
comparison (it cannot differentiate anyone) and reported in ``excluded_parameters``.

All arithmetic uses :class:`~decimal.Decimal` and every ordering is broken deterministically,
so repeated runs on the same request are identical. The result is informational only: it never
labels a product "healthiest"; the top product simply "ranks highest based on your selected
parameters".
"""

from __future__ import annotations

from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from app.comparison.units import (
    NormalizationStatus,
    NormalizedValue,
    normalize_input,
    normalize_value,
)
from app.core.enums import (
    ComparisonOutcome,
    ComparisonPriority,
    ComparisonStatus,
    DeclarationStatus,
    NutritionParameter,
    ParameterDirection,
)
from app.schemas.comparison import (
    ComparisonRequest,
    ComparisonResult,
    ExcludedParameter,
    ParameterScore,
    ProductComparisonResult,
    RankEntry,
)

# The single source of truth mapping a consumer priority to the parameter it scores and the
# direction that is preferable. Verified against the approved architecture and the user spec.
PRIORITY_SPEC: dict[ComparisonPriority, tuple[NutritionParameter, ParameterDirection]] = {
    ComparisonPriority.LOWER_CALORIES: (NutritionParameter.CALORIES, ParameterDirection.LOWER_BETTER),
    ComparisonPriority.LOWER_SUGAR: (NutritionParameter.SUGAR, ParameterDirection.LOWER_BETTER),
    ComparisonPriority.LOWER_ADDED_SUGAR: (NutritionParameter.ADDED_SUGAR, ParameterDirection.LOWER_BETTER),
    ComparisonPriority.HIGHER_PROTEIN: (NutritionParameter.PROTEIN, ParameterDirection.HIGHER_BETTER),
    ComparisonPriority.LOWER_CARBOHYDRATES: (NutritionParameter.CARBOHYDRATES, ParameterDirection.LOWER_BETTER),
    ComparisonPriority.LOWER_FAT: (NutritionParameter.FAT, ParameterDirection.LOWER_BETTER),
    ComparisonPriority.LOWER_SATURATED_FAT: (NutritionParameter.SATURATED_FAT, ParameterDirection.LOWER_BETTER),
    ComparisonPriority.LOWER_TRANS_FAT: (NutritionParameter.TRANS_FAT, ParameterDirection.LOWER_BETTER),
    ComparisonPriority.HIGHER_FIBER: (NutritionParameter.FIBER, ParameterDirection.HIGHER_BETTER),
    ComparisonPriority.LOWER_SODIUM: (NutritionParameter.SODIUM, ParameterDirection.LOWER_BETTER),
}

# Displayed scores are rounded to this resolution; it also defines "equal" for tie detection.
_SCORE_PRECISION = Decimal("0.000001")
# Score given to every product when a parameter's comparable values are all equal.
_DEGENERATE_SCORE = Decimal("0.5")


def _q(value: Decimal) -> Decimal:
    """Quantise a score-like Decimal to the fixed display/tie precision, half-up."""
    return value.quantize(_SCORE_PRECISION, rounding=ROUND_HALF_UP)


def _parameter_label(parameter: NutritionParameter) -> str:
    return parameter.value.lower().replace("_", " ")


def _priority_label(priority: ComparisonPriority) -> str:
    return priority.value.lower().replace("_", " ")


def _join_names(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def score_comparison(request: ComparisonRequest) -> ComparisonResult:
    """Rank the requested products on the selected priorities, deterministically.

    Consumes a validated :class:`~app.schemas.comparison.ComparisonRequest` and returns a fully
    explainable :class:`~app.schemas.comparison.ComparisonResult`. It performs no I/O, calls
    no model, and never mutates the request.
    """
    products = request.products

    # --- Single product handling ---
    if len(products) == 1:
        p = products[0]
        pid = p.product_id
        name = p.product_name
        selected = [(*PRIORITY_SPEC[pw.priority], pw.weight) for pw in request.priorities]

        parameter_scores: list[ParameterScore] = []
        available_params: list[NutritionParameter] = []
        missing_params: list[NutritionParameter] = []

        for parameter, direction, weight in selected:
            if parameter in p.values:
                nv = normalize_input(parameter, p.values[parameter])
                if nv.is_comparable:
                    available_params.append(parameter)
                    parameter_scores.append(
                        ParameterScore(
                            parameter=parameter,
                            direction=direction,
                            canonical_value=nv.canonical_value,
                            unit=nv.canonical_unit,
                            status=nv.original_status,
                            included=True,
                            normalized_score=1.0,
                            weight=weight,
                            effective_weight=1.0,
                            weighted_contribution=1.0,
                            note="Single product evaluation.",
                        )
                    )
                    continue

            missing_params.append(parameter)
            status_val = p.values[parameter].status if parameter in p.values else DeclarationStatus.NOT_DETECTED
            parameter_scores.append(
                ParameterScore(
                    parameter=parameter,
                    direction=direction,
                    canonical_value=None,
                    unit=None,
                    status=status_val,
                    included=False,
                    normalized_score=None,
                    weight=weight,
                    effective_weight=None,
                    weighted_contribution=None,
                    note="Not detected for single product.",
                )
            )

        coverage = len(available_params) / len(selected) if selected else 0.0
        score = 1.0 if available_params else None
        single_expl = f"{name} evaluated. There are no competing products to rank against."

        product_result = ProductComparisonResult(
            product_id=pid,
            product_name=name,
            rank=1,
            score=score,
            outcome=ComparisonOutcome.SINGLE_PRODUCT,
            coverage=float(_q(Decimal(str(coverage)))),
            parameter_scores=parameter_scores,
            available_parameters=available_params,
            missing_parameters=missing_params,
            highlights=[],
            warnings=[],
            explanation=single_expl,
        )

        return ComparisonResult(
            status=ComparisonStatus.SINGLE_PRODUCT,
            winner=None,  # Do not fabricate a comparative winner for a single product
            ranking=[RankEntry(rank=1, product_id=pid, product_name=name, score=score)],
            products=[product_result],
            active_parameters=available_params,
            excluded_parameters=[],
            priorities_used=list(request.priorities),
            explanation=single_expl,
            trade_offs=[],
        )

    # --- Multi-product comparison ---
    name_of = {p.product_id: p.product_name for p in products}
    order_index = {p.product_id: i for i, p in enumerate(products)}

    selected = [(*PRIORITY_SPEC[pw.priority], pw.weight) for pw in request.priorities]

    # Stage 1-2: unit-normalise every selected value for every product.
    normalized: dict[str, dict[NutritionParameter, NormalizedValue]] = {}
    for product in products:
        normalized[product.product_id] = {
            parameter: (
                normalize_input(parameter, product.values[parameter])
                if parameter in product.values
                else normalize_value(parameter, None, None, DeclarationStatus.NOT_DETECTED)
            )
            for parameter, _direction, _weight in selected
        }

    # Decide which parameters can differentiate the products (>= 2 comparable values)
    active: list[tuple[NutritionParameter, ParameterDirection, int]] = []
    excluded: list[ExcludedParameter] = []
    bounds: dict[NutritionParameter, tuple[Decimal, Decimal]] = {}
    for parameter, direction, weight in selected:
        pool = [
            normalized[p.product_id][parameter].canonical_value
            for p in products
            if normalized[p.product_id][parameter].is_comparable
        ]
        if len(pool) < 2:
            excluded.append(
                ExcludedParameter(
                    parameter=parameter,
                    reason=(
                        "Declared with a comparable value by fewer than two products, "
                        "so it cannot differentiate them."
                    ),
                )
            )
            continue
        bounds[parameter] = (min(pool), max(pool))
        active.append((parameter, direction, weight))

    def _relative_score(parameter: NutritionParameter, direction: ParameterDirection, value: Decimal) -> Decimal:
        low, high = bounds[parameter]
        if high == low:  # every comparable value is equal -> neutral score 0.5
            return _DEGENERATE_SCORE
        if direction is ParameterDirection.HIGHER_BETTER:
            return (value - low) / (high - low)
        return (high - value) / (high - low)

    # Highlights
    highlights: dict[str, list[str]] = {p.product_id: [] for p in products}
    for parameter, direction, _weight in active:
        low, high = bounds[parameter]
        if high == low:
            continue
        best = low if direction is ParameterDirection.LOWER_BETTER else high
        lead_word = "Lowest" if direction is ParameterDirection.LOWER_BETTER else "Highest"
        for p in products:
            nv = normalized[p.product_id][parameter]
            if nv.is_comparable and nv.canonical_value == best:
                highlights[p.product_id].append(
                    f"{lead_word} {_parameter_label(parameter)}"
                )

    # Stage 3-4: per product, build parameter scores and weighted final score.
    aggregates: dict[str, dict] = {}
    for product in products:
        pid = product.product_id
        available_weight = sum(
            weight for parameter, _direction, weight in active if normalized[pid][parameter].is_comparable
        )

        parameter_scores: list[ParameterScore] = []
        available_params: list[NutritionParameter] = []
        missing_params: list[NutritionParameter] = []
        warnings: list[str] = []
        final = Decimal(0)

        for parameter, direction, weight in active:
            nv = normalized[pid][parameter]
            if nv.is_comparable and available_weight > 0:
                raw = _relative_score(parameter, direction, nv.canonical_value)
                effective = Decimal(weight) / Decimal(available_weight)
                contribution = raw * effective
                final += contribution
                available_params.append(parameter)
                parameter_scores.append(
                    ParameterScore(
                        parameter=parameter,
                        direction=direction,
                        canonical_value=nv.canonical_value,
                        unit=nv.canonical_unit,
                        status=nv.original_status,
                        included=True,
                        normalized_score=float(_q(raw)),
                        weight=weight,
                        effective_weight=float(_q(effective)),
                        weighted_contribution=float(_q(contribution)),
                        note=nv.detail,
                    )
                )
            else:
                missing_params.append(parameter)
                parameter_scores.append(
                    ParameterScore(
                        parameter=parameter,
                        direction=direction,
                        canonical_value=None,
                        unit=None,
                        status=nv.original_status,
                        included=False,
                        normalized_score=None,
                        weight=weight,
                        effective_weight=None,
                        weighted_contribution=None,
                        note=nv.detail,
                    )
                )
                if nv.status in (NormalizationStatus.UNSUPPORTED_UNIT, NormalizationStatus.INVALID_VALUE):
                    warnings.append(f"{_parameter_label(parameter)}: {nv.detail}")

        coverage = Decimal(len(available_params)) / Decimal(len(active)) if active else Decimal(0)
        score = _q(final) if available_weight > 0 else None

        aggregates[pid] = {
            "parameter_scores": parameter_scores,
            "available_params": available_params,
            "missing_params": missing_params,
            "warnings": warnings,
            "coverage": float(_q(coverage)),
            "score": score,
        }

    # Stage 5: rank by score descending
    rankable = [pid for pid, agg in aggregates.items() if agg["score"] is not None]
    rankable.sort(key=lambda pid: (-aggregates[pid]["score"], order_index[pid]))

    rank_of: dict[str, int] = {}
    for position, pid in enumerate(rankable):
        if position > 0 and aggregates[pid]["score"] == aggregates[rankable[position - 1]]["score"]:
            rank_of[pid] = rank_of[rankable[position - 1]]
        else:
            rank_of[pid] = position + 1
    shared = Counter(rank_of.values())

    status = ComparisonStatus.COMPLETED if (active and rankable) else ComparisonStatus.INSUFFICIENT_DATA

    main_explanation, winner, trade_offs = _build_explanations(
        status, rankable, rank_of, name_of, request, active, normalized
    )

    product_results: list[ProductComparisonResult] = []
    for product in products:
        pid = product.product_id
        agg = aggregates[pid]
        if agg["score"] is None:
            outcome = ComparisonOutcome.COULD_NOT_RANK
        elif shared[rank_of[pid]] > 1:
            outcome = ComparisonOutcome.TIED
        else:
            outcome = ComparisonOutcome.RANKED

        p_explanation = f"{name_of[pid]} ranks #{rank_of[pid]} with a score of {agg['score']}." if agg["score"] is not None else f"{name_of[pid]} could not be ranked."

        product_results.append(
            ProductComparisonResult(
                product_id=pid,
                product_name=name_of[pid],
                rank=rank_of.get(pid),
                score=float(agg["score"]) if agg["score"] is not None else None,
                outcome=outcome,
                coverage=agg["coverage"],
                parameter_scores=agg["parameter_scores"],
                available_parameters=agg["available_params"],
                missing_parameters=agg["missing_params"],
                highlights=highlights[pid],
                warnings=agg["warnings"],
                explanation=p_explanation,
            )
        )

    ranking = [
        RankEntry(
            rank=rank_of[pid],
            product_id=pid,
            product_name=name_of[pid],
            score=float(aggregates[pid]["score"]),
        )
        for pid in rankable
    ]

    return ComparisonResult(
        status=status,
        winner=winner,
        ranking=ranking,
        products=product_results,
        active_parameters=[parameter for parameter, _direction, _weight in active],
        excluded_parameters=excluded,
        priorities_used=list(request.priorities),
        explanation=main_explanation,
        trade_offs=trade_offs,
    )


def _build_explanations(
    status: ComparisonStatus,
    rankable: list[str],
    rank_of: dict[str, int],
    name_of: dict[str, str],
    request: ComparisonRequest,
    active: list[tuple[NutritionParameter, ParameterDirection, int]],
    normalized: dict[str, dict[NutritionParameter, NormalizedValue]],
) -> tuple[str, str | None, list[str]]:
    """Build deterministic main explanation, winner, and trade-offs."""
    if status is ComparisonStatus.INSUFFICIENT_DATA:
        return (
            "These products could not be ranked because fewer than two of them share "
            "comparable values for the selected parameters.",
            None,
            [],
        )

    leaders_ids = [pid for pid in rankable if rank_of[pid] == 1]
    leaders_names = [name_of[pid] for pid in leaders_ids]

    if len(leaders_ids) != 1:
        priorities_text = ", ".join(_priority_label(pw.priority) for pw in request.priorities)
        expl = f"{_join_names(leaders_names)} rank highest (tied) based on your selected parameters ({priorities_text})."
        return expl, None, []

    winner_id = leaders_ids[0]
    winner_name = name_of[winner_id]
    trade_offs: list[str] = []

    # Identify parameters where winner is strictly best
    winner_best_params: list[str] = []
    for param, direction, _w in active:
        w_nv = normalized[winner_id][param]
        if w_nv.is_comparable:
            vals = [normalized[pid][param].canonical_value for pid in rankable if normalized[pid][param].is_comparable]
            if vals:
                best_val = min(vals) if direction is ParameterDirection.LOWER_BETTER else max(vals)
                if w_nv.canonical_value == best_val and len(set(vals)) > 1:
                    prefix = "lower" if direction is ParameterDirection.LOWER_BETTER else "higher"
                    winner_best_params.append(f"{prefix} {_parameter_label(param)}")

    other_ids = [pid for pid in rankable if rank_of[pid] > 1]
    for other_id in other_ids:
        other_name = name_of[other_id]
        other_better_params: list[str] = []
        for param, direction, _w in active:
            w_nv = normalized[winner_id][param]
            o_nv = normalized[other_id][param]
            if w_nv.is_comparable and o_nv.is_comparable:
                if direction is ParameterDirection.LOWER_BETTER and o_nv.canonical_value < w_nv.canonical_value:
                    other_better_params.append(f"lower {_parameter_label(param)}")
                elif direction is ParameterDirection.HIGHER_BETTER and o_nv.canonical_value > w_nv.canonical_value:
                    other_better_params.append(f"higher {_parameter_label(param)}")

        if other_better_params:
            w_str = _join_names(winner_best_params) if winner_best_params else "higher overall score"
            o_str = _join_names(other_better_params)
            trade_offs.append(
                f"{winner_name} ranks higher based on {w_str}, although {other_name} has {o_str}."
            )

    priorities_text = ", ".join(_priority_label(pw.priority) for pw in request.priorities)
    if trade_offs:
        main_explanation = f"{trade_offs[0]}"
    else:
        main_explanation = f"{winner_name} ranks highest based on your selected parameters ({priorities_text})."

    return main_explanation, winner_name, trade_offs
