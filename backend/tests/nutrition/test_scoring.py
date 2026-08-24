"""Deterministic scoring / ranking core.

Covers required scenarios (8) lower-is-better, (9) higher-is-better,
(3) equal values (non-differentiating), and the missing-data fairness rule
(a product is scored only on the parameters it has, weights renormalised).
"""

from __future__ import annotations

import pytest

from app.nutrition.comparison.parameters import Direction, Parameter
from app.nutrition.comparison.schema import ComparisonPriority
from app.nutrition.comparison.scoring import (
    build_scoreboard,
    resolve_priorities,
)
from app.nutrition.comparison.scoring_normalization import build_normalized_table
from app.nutrition.comparison.schema import ProductNutritionInput


def _table(products: dict[str, dict]):
    inputs = [
        ProductNutritionInput(product_id=pid, nutrients=nutrients)
        for pid, nutrients in products.items()
    ]
    table, _warnings = build_normalized_table(inputs)
    return list(products.keys()), table


def _score_map(board):
    return {p.product_id: p.score for p in board.products}


def test_lower_is_better_ranks_smallest_first():
    ids, table = _table(
        {
            "A": {"sugar": 10},
            "B": {"sugar": 2},
            "C": {"sugar": 6},
        }
    )
    resolved = resolve_priorities([ComparisonPriority(parameter=Parameter.SUGAR)])
    board = build_scoreboard(ids, resolved, table)

    assert [p.product_id for p in board.products] == ["B", "C", "A"]
    scores = _score_map(board)
    assert scores["B"] == pytest.approx(100.0)  # lowest sugar -> best
    assert scores["A"] == pytest.approx(0.0)  # highest sugar -> worst
    assert scores["C"] == pytest.approx(50.0)  # midpoint


def test_higher_is_better_ranks_largest_first():
    ids, table = _table(
        {
            "A": {"protein": 5},
            "B": {"protein": 20},
            "C": {"protein": 12.5},
        }
    )
    resolved = resolve_priorities([ComparisonPriority(parameter=Parameter.PROTEIN)])
    board = build_scoreboard(ids, resolved, table)

    assert [p.product_id for p in board.products] == ["B", "C", "A"]
    scores = _score_map(board)
    assert scores["B"] == pytest.approx(100.0)  # most protein -> best
    assert scores["A"] == pytest.approx(0.0)
    assert scores["C"] == pytest.approx(50.0)


def test_direction_override_flips_preference():
    ids, table = _table({"A": {"protein": 5}, "B": {"protein": 20}})
    resolved = resolve_priorities(
        [ComparisonPriority(parameter=Parameter.PROTEIN, direction=Direction.LOWER_IS_BETTER)]
    )
    board = build_scoreboard(ids, resolved, table)
    # With LOWER_IS_BETTER forced, the 5g product now wins.
    assert board.products[0].product_id == "A"


def test_equal_values_are_non_differentiating():
    ids, table = _table({"A": {"sugar": 5}, "B": {"sugar": 5}})
    resolved = resolve_priorities([ComparisonPriority(parameter=Parameter.SUGAR)])
    board = build_scoreboard(ids, resolved, table)

    sugar = next(s for s in board.parameters if s.parameter is Parameter.SUGAR)
    assert sugar.differentiating is False
    assert sugar.note is not None
    # No parameter separates them -> both unscored, and it's a tie.
    assert all(p.score is None for p in board.products)
    assert board.tie is True


def test_single_participant_parameter_is_non_differentiating():
    # Only A has fiber; it cannot differentiate on its own.
    ids, table = _table({"A": {"sugar": 3, "fiber": 8}, "B": {"sugar": 9}})
    resolved = resolve_priorities(
        [
            ComparisonPriority(parameter=Parameter.SUGAR),
            ComparisonPriority(parameter=Parameter.FIBER),
        ]
    )
    board = build_scoreboard(ids, resolved, table)

    fiber = next(s for s in board.parameters if s.parameter is Parameter.FIBER)
    assert fiber.differentiating is False
    # Ranking is decided by sugar alone; A (3g) beats B (9g).
    assert board.products[0].product_id == "A"


def test_missing_parameter_does_not_penalise_with_zero():
    # A is missing protein. It must be scored on sugar only, not given sugar=win
    # + protein=0. Its coverage should reflect the missing half.
    ids, table = _table(
        {
            "A": {"sugar": 2},  # best sugar, no protein
            "B": {"sugar": 10, "protein": 20},  # worst sugar, only protein
        }
    )
    resolved = resolve_priorities(
        [
            ComparisonPriority(parameter=Parameter.SUGAR),
            ComparisonPriority(parameter=Parameter.PROTEIN),
        ]
    )
    board = build_scoreboard(ids, resolved, table)
    by_id = {p.product_id: p for p in board.products}

    # Neither sugar nor protein has 2 participants? Sugar has both (2 vs 10) so
    # it differentiates; protein has only B so it does not.
    assert by_id["A"].score == pytest.approx(100.0)  # wins the only differentiating param
    assert by_id["B"].score == pytest.approx(0.0)
    # Protein was non-differentiating, so coverage is measured over sugar only:
    assert by_id["A"].coverage == pytest.approx(1.0)
    assert Parameter.PROTEIN not in by_id["A"].scored_parameters


def test_partial_coverage_is_reported():
    # Both differentiate on sugar; only B and C differentiate on protein.
    ids, table = _table(
        {
            "A": {"sugar": 1},  # no protein
            "B": {"sugar": 5, "protein": 10},
            "C": {"sugar": 9, "protein": 20},
        }
    )
    resolved = resolve_priorities(
        [
            ComparisonPriority(parameter=Parameter.SUGAR, weight=1),
            ComparisonPriority(parameter=Parameter.PROTEIN, weight=1),
        ]
    )
    board = build_scoreboard(ids, resolved, table)
    by_id = {p.product_id: p for p in board.products}

    # A has data for sugar (weight 0.5) only -> coverage 0.5.
    assert by_id["A"].coverage == pytest.approx(0.5)
    assert Parameter.PROTEIN in by_id["A"].not_detected_parameters
    # B and C have both -> coverage 1.0.
    assert by_id["B"].coverage == pytest.approx(1.0)
    assert by_id["C"].coverage == pytest.approx(1.0)


def test_weights_change_ranking():
    ids, table = _table(
        {
            "A": {"sugar": 0, "protein": 0},  # best sugar, worst protein
            "B": {"sugar": 10, "protein": 10},  # worst sugar, best protein
        }
    )
    # Weight protein heavily -> B should win despite its high sugar.
    resolved = resolve_priorities(
        [
            ComparisonPriority(parameter=Parameter.SUGAR, weight=1),
            ComparisonPriority(parameter=Parameter.PROTEIN, weight=9),
        ]
    )
    board = build_scoreboard(ids, resolved, table)
    assert board.products[0].product_id == "B"
    assert board.products[0].score == pytest.approx(90.0)


def test_weights_are_rescaled_to_sum_one():
    ids, table = _table({"A": {"sugar": 1}, "B": {"sugar": 2}})
    resolved = resolve_priorities(
        [ComparisonPriority(parameter=Parameter.SUGAR, weight=7)]  # absolute magnitude irrelevant
    )
    board = build_scoreboard(ids, resolved, table)
    sugar = next(s for s in board.parameters if s.parameter is Parameter.SUGAR)
    assert sugar.weight == pytest.approx(1.0)


def test_tie_is_flagged_and_keeps_input_order():
    # Mirror-image products: A best sugar/worst protein, B worst sugar/best protein.
    ids, table = _table(
        {
            "A": {"sugar": 0, "protein": 0},
            "B": {"sugar": 10, "protein": 10},
        }
    )
    resolved = resolve_priorities(
        [
            ComparisonPriority(parameter=Parameter.SUGAR, weight=1),
            ComparisonPriority(parameter=Parameter.PROTEIN, weight=1),
        ]
    )
    board = build_scoreboard(ids, resolved, table)
    assert board.tie is True
    assert board.products[0].score == pytest.approx(board.products[1].score)
    assert board.products[0].product_id == "A"  # input order preserved


def test_determinism_same_input_same_output():
    ids, table = _table({"A": {"sugar": 3}, "B": {"sugar": 7}, "C": {"sugar": 1}})
    resolved = resolve_priorities([ComparisonPriority(parameter=Parameter.SUGAR)])
    first = build_scoreboard(ids, resolved, table)
    second = build_scoreboard(ids, resolved, table)
    assert [p.product_id for p in first.products] == [p.product_id for p in second.products]
    assert _score_map(first) == _score_map(second)


def test_duplicate_priority_last_wins():
    resolved = resolve_priorities(
        [
            ComparisonPriority(parameter=Parameter.SUGAR, direction=Direction.LOWER_IS_BETTER),
            ComparisonPriority(parameter=Parameter.SUGAR, direction=Direction.HIGHER_IS_BETTER),
        ]
    )
    assert len(resolved) == 1
    assert resolved[0].direction is Direction.HIGHER_IS_BETTER
