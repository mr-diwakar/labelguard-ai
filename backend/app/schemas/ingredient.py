from app.schemas.common import APIModel


class IngredientItem(APIModel):
    """Teammate 2 contract. An empty list is a valid result."""

    name: str
    raw_text: str | None = None
