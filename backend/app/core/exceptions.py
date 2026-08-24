"""Application errors. The JSON envelope lives in app.schemas.common."""

from typing import Any

from app.schemas.common import ErrorResponse


class AppError(Exception):
    """
    Domain/application failure that is safe to return to a client.

    Never put stack traces, secrets, or raw exception text in message or details.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code


def error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Builds the JSON body every error handler must return."""
    return ErrorResponse.model_validate(
        {"error": {"code": code, "message": message, "details": details or {}}}
    ).model_dump()


def not_found(resource: str, resource_id: str | None = None) -> AppError:
    details: dict[str, Any] = {"resource": resource}
    if resource_id is not None:
        details["id"] = resource_id

    return AppError(
        "NOT_FOUND",
        f"{resource} was not found.",
        details=details,
        status_code=404,
    )
