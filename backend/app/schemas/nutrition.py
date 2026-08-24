from app.schemas.common import APIModel


class NutritionResult(APIModel):
    """Teammate 2 contract. Absent or unavailable must not block legal analysis."""

    available: bool = False
    payload: dict | None = None
