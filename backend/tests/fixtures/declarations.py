from app.schemas.declaration import Declaration


def declaration(
    field: str,
    value: str | None,
    *,
    status: str = "DETECTED",
    confidence: float | None = 0.98,
    bbox: list[int] | None = None,
) -> Declaration:
    return Declaration.model_validate(
        {
            "field": field,
            "value": value,
            "confidence": confidence,
            "source": "OCR",
            "bbox": bbox or [10, 20, 30, 40],
            "status": status,
        }
    )


def detected(field: str, value: str, confidence: float = 0.98) -> Declaration:
    return declaration(field, value, status="DETECTED", confidence=confidence)


def not_detected(field: str, confidence: float = 0.40) -> Declaration:
    return declaration(field, None, status="NOT_DETECTED", confidence=confidence)


def confirmed_absent(field: str) -> Declaration:
    """Extractor is confident the field is not on a readable label."""
    return declaration(field, None, status="NOT_DETECTED", confidence=0.95)


HOUSEHOLD_PASS = {
    "manufacturer": {"value": "Acme Packers", "status": "DETECTED", "confidence": 0.98},
    "commodity_name": {"value": "Bath soap", "status": "DETECTED", "confidence": 0.98},
    "net_quantity": {"value": "100 g", "status": "DETECTED", "confidence": 0.98},
    "manufacture_date": {"value": "07/2026", "status": "DETECTED", "confidence": 0.98},
    "mrp": {"value": "50", "status": "DETECTED", "confidence": 0.98},
    "consumer_care": {"value": "Acme Care 1800123456 care@acme.test", "status": "DETECTED", "confidence": 0.98},
}
