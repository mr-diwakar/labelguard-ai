"""
Deterministic, explainable scoring and ranking.

Method (documented so it can be defended to a judge and reproduced by hand):

1. Unit normalisation has already happened upstream; every value is in its
   parameter's canonical unit.

2. Per selected parameter, look only at *participants* — products that actually
   have a usable value. Min-max normalise each value to a sub-score in [0, 1]
   where 1 is the most preferred:

       LOWER_IS_BETTER :  sub = (max - v) / (max - min)
       HIGHER_IS_BETTER:  sub = (v - min) / (max - min)

   If fewer than two products participate, or every value is equal
   (max == min), the parameter cannot separate products: it is marked
   non-differentiating and excluded from scoring (but still reported). When it
   is differentiating but a single product happens to tie the extreme, that is
   a real sub-score, not an exclusion.

3. Per product, combine the sub-scores of the parameters it HAS data for, using
   the caller's weights rescaled to sum to 1 across the differentiating
   parameters. Crucially, the denominator is the weight of the parameters the
   product actually has, so a product is never penalised with an implicit 0 for
   a missing parameter, nor rewarded for one:

       score(X) = Σ_{p ∈ have(X)} w_p · sub(X, p)  /  Σ_{p ∈ have(X)} w_p

   Scores are reported on a 0..100 scale. ``coverage`` records the fraction of
   differentiating weight the product had data for, so a high score built on
   thin coverage is visible rather than hidden.

4. Rank by score descending. Ties (equal rounded score) keep input order and
   are flagged.

No randomness, no LLM, no medical judgement. Everything is a pure function of
the inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.nutrition.comparison.parameters import Direction, Parameter, default_direction
from app.nutrition.comparison.schema import ComparisonPriority
from app.nutrition.comparison.scoring_normalization import NormalizedTable
from app.nutrition.comparison.units import NormalizationStatus

# Scores are rounded to this many decimals before ranking so floating-point
# noise does not manufacture a false winner between genuinely tied products.
_SCORE_DECIMALS = 6


@dataclass(frozen=True)
class ResolvedPriority:
    parameter: Parameter
    weight: float
    direction: Direction


@dataclass
class ParameterScoring:
    parameter: Parameter
    direction: Direction
    weight: float  # rescaled across differentiating parameters, 0..1
    differentiating: bool
    participating_product_ids: list[str] = field(default_factory=list)
    not_detected_product_ids: list[str] = field(default_factory=list)
    sub_scores: dict[str, float] = field(default_factory=dict)  # product_id -> 0..1
    best_product_id: str | None = None
    note: str | None = None


@dataclass
class ProductScore:
    product_id: str
    score: float | None  # 0..100
    coverage: float  # 0..1 over differentiating weight
    scored_parameters: list[Parameter] = field(default_factory=list)
    not_detected_parameters: list[Parameter] = field(default_factory=list)


@dataclass
class ScoreBoard:
    parameters: list[ParameterScoring]
    products: list[ProductScore]  # ranked, best first
    tie: bool


def resolve_priorities(priorities: list[ComparisonPriority]) -> list[ResolvedPriority]:
    """Deduplicate priorities (last wins) and fill in default directions."""

    resolved: dict[Parameter, ResolvedPriority] = {}
    for priority in priorities:
        resolved[priority.parameter] = ResolvedPriority(
            parameter=priority.parameter,
            weight=float(priority.weight),
            direction=priority.direction or default_direction(priority.parameter),
        )
    return list(resolved.values())


def _usable_value(table: NormalizedTable, product_id: str, parameter: Parameter) -> float | None:
    cell = table.get(product_id, {}).get(parameter)
    if cell is None or cell.status is not NormalizationStatus.OK or cell.value is None:
        return None
    return cell.value


def _score_parameter(
    priority: ResolvedPriority,
    product_ids: list[str],
    table: NormalizedTable,
) -> ParameterScoring:
    values: dict[str, float] = {}
    not_detected: list[str] = []
    for product_id in product_ids:
        value = _usable_value(table, product_id, priority.parameter)
        if value is None:
            not_detected.append(product_id)
        else:
            values[product_id] = value

    scoring = ParameterScoring(
        parameter=priority.parameter,
        direction=priority.direction,
        weight=0.0,
        differentiating=False,
        participating_product_ids=list(values.keys()),
        not_detected_product_ids=not_detected,
    )

    if len(values) < 2:
        scoring.note = (
            "Not enough products have this value to compare, so it does not affect the ranking."
        )
        return scoring

    lo = min(values.values())
    hi = max(values.values())
    if hi == lo:
        scoring.note = "All compared products share the same value, so it does not affect the ranking."
        # Best is ambiguous when everyone is equal; leave best_product_id unset.
        return scoring

    span = hi - lo
    for product_id, value in values.items():
        if priority.direction is Direction.LOWER_IS_BETTER:
            sub = (hi - value) / span
        else:
            sub = (value - lo) / span
        scoring.sub_scores[product_id] = sub

    scoring.differentiating = True
    # Best participant for this parameter: highest sub-score, input order breaks ties.
    scoring.best_product_id = max(
        scoring.participating_product_ids,
        key=lambda pid: (scoring.sub_scores[pid], -product_ids.index(pid)),
    )
    return scoring


def _rescale_weights(scorings: list[ParameterScoring], resolved: list[ResolvedPriority]) -> None:
    weight_by_param = {item.parameter: item.weight for item in resolved}
    differentiating = [s for s in scorings if s.differentiating]
    total = sum(weight_by_param[s.parameter] for s in differentiating)
    if total <= 0:
        return
    for scoring in differentiating:
        scoring.weight = weight_by_param[scoring.parameter] / total


def _score_products(
    product_ids: list[str],
    scorings: list[ParameterScoring],
) -> list[ProductScore]:
    differentiating = [s for s in scorings if s.differentiating]
    results: list[ProductScore] = []

    for product_id in product_ids:
        weighted_sum = 0.0
        weight_have = 0.0
        scored: list[Parameter] = []

        for scoring in differentiating:
            sub = scoring.sub_scores.get(product_id)
            if sub is None:
                continue
            weighted_sum += scoring.weight * sub
            weight_have += scoring.weight
            scored.append(scoring.parameter)

        # Transparency list: every *selected* priority this product had no usable
        # value for, whether or not that parameter ended up differentiating. This
        # is what the consumer sees ("protein not detected"), distinct from the
        # scoring-relevant coverage below.
        missing = [s.parameter for s in scorings if product_id in s.not_detected_product_ids]

        if weight_have <= 0:
            results.append(ProductScore(product_id, None, 0.0, scored, missing))
            continue

        raw_score = weighted_sum / weight_have  # 0..1, renormalised over available weight
        results.append(
            ProductScore(
                product_id=product_id,
                score=round(raw_score * 100, _SCORE_DECIMALS),
                coverage=weight_have,  # differentiating weights already sum to 1
                scored_parameters=scored,
                not_detected_parameters=missing,
            )
        )
    return results


def _rank(products: list[ProductScore], product_ids: list[str]) -> tuple[list[ProductScore], bool]:
    def sort_key(item: ProductScore) -> tuple[int, float, float, int]:
        has_score = 0 if item.score is not None else 1  # scored products first
        score = item.score if item.score is not None else 0.0
        # Higher score, then higher coverage, then original input order.
        return (has_score, -score, -item.coverage, product_ids.index(item.product_id))

    ranked = sorted(products, key=sort_key)

    top = [p for p in ranked if p.score is not None]
    tie = len(top) >= 2 and top[0].score == top[1].score and top[0].coverage == top[1].coverage
    return ranked, tie


def build_scoreboard(
    product_ids: list[str],
    resolved: list[ResolvedPriority],
    table: NormalizedTable,
) -> ScoreBoard:
    scorings = [_score_parameter(priority, product_ids, table) for priority in resolved]
    _rescale_weights(scorings, resolved)
    products = _score_products(product_ids, scorings)
    ranked, tie = _rank(products, product_ids)

    # Comparable-but-equal case: two or more products were measured against at
    # least one shared parameter, nothing separated them, and none could be
    # scored. That is a genuine tie (they are equal on the chosen criteria), as
    # opposed to being merely incomparable (no shared parameter at all).
    if not tie and len(product_ids) >= 2 and all(p.score is None for p in products):
        has_comparable_parameter = any(
            len(s.participating_product_ids) >= 2 for s in scorings
        )
        tie = has_comparable_parameter

    return ScoreBoard(parameters=scorings, products=ranked, tie=tie)
