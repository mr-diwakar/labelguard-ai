"""
Turn a scoreboard into consumer-facing, comparative explanations.

Language rule (from PROJECT_CONTEXT): never "healthiest" or a medical verdict.
Only relative statements about the selected parameters, e.g. "Lowest sugar",
"Higher calories than Product A". These are informational, not dietary advice.
"""

from __future__ import annotations

from app.nutrition.comparison.parameters import Direction, display_name
from app.nutrition.comparison.scoring import ParameterScoring

_BEST_EPSILON = 1e-9


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _superlatives(direction: Direction) -> tuple[str, str]:
    """Return (best_word, worse_word) for a direction."""

    if direction is Direction.LOWER_IS_BETTER:
        return "Lowest", "Higher"
    return "Highest", "Lower"


def headline(winner_display_name: str) -> str:
    return f"{winner_display_name} ranks highest based on your selected parameters."


def build_highlights(
    product_id: str,
    scorings: list[ParameterScoring],
    name_by_id: dict[str, str],
) -> list[str]:
    """Per-product ✓/⚠/• lines, in the caller's priority order."""

    lines: list[str] = []
    for scoring in scorings:
        name = display_name(scoring.parameter)

        if not scoring.differentiating:
            if product_id in scoring.participating_product_ids and len(scoring.participating_product_ids) >= 2:
                lines.append(f"• Equal {name} across products")
            continue

        sub = scoring.sub_scores.get(product_id)
        if sub is None:
            lines.append(f"⚠ {_cap(name)} not detected")
            continue

        best_word, worse_word = _superlatives(scoring.direction)
        if sub >= 1.0 - _BEST_EPSILON:
            tied = sum(1 for value in scoring.sub_scores.values() if value >= 1.0 - _BEST_EPSILON) > 1
            if tied:
                lines.append(f"✓ Tied for {best_word.lower()} {name}")
            else:
                lines.append(f"✓ {best_word} {name}")
        else:
            best_name = name_by_id.get(scoring.best_product_id or "", scoring.best_product_id or "")
            lines.append(f"⚠ {worse_word} {name} than {best_name}")

    return lines
