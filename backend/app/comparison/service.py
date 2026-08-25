"""Multi-product nutrition comparison service (Phase 3).

Orchestrates the complete comparison pipeline:
    Input -> Validation -> Unit Normalisation -> Parameter Normalisation
          -> Priority/Weight Processing -> Scoring -> Ranking -> Explanation -> Result

Guarantees:
    * Accepts already-extracted nutrition data.
    * Does NOT perform OCR or extraction.
    * Does NOT mutate original nutrition objects.
    * Completely deterministic and LLM-free.
"""

from app.comparison.scoring import score_comparison
from app.schemas.comparison import ComparisonRequest, ComparisonResult


class ComparisonService:
    """Service orchestrating multi-product nutrition comparisons."""

    @classmethod
    def compare(cls, request: ComparisonRequest) -> ComparisonResult:
        """Run multi-product nutrition comparison.

        Args:
            request: Validated ComparisonRequest containing products and selected priorities.

        Returns:
            ComparisonResult containing deterministic rankings, scores, parameter breakdowns,
            explanations, trade-offs, and disclaimer.
        """
        return score_comparison(request)
