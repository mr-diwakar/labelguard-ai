"""Phase 2: every failure uses the same error envelope and never leaks internals."""

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import AppError
from app.main import create_app


class _SampleBody(BaseModel):
    name: str


def _client() -> TestClient:
    app = create_app(Settings(app_env="development", log_level="INFO"))

    @app.post("/_test/echo")
    def echo(body: _SampleBody) -> dict[str, str]:
        return {"name": body.name}

    @app.get("/_test/app-error")
    def raise_app_error() -> None:
        raise AppError(
            "IMAGE_TOO_BLURRY",
            "The image is too blurry to analyze reliably.",
            details={"reason": "low_sharpness"},
            status_code=422,
        )

    @app.get("/_test/boom")
    def raise_unexpected() -> None:
        raise RuntimeError("secret database password=super-secret should never reach the client")

    return TestClient(app, raise_server_exceptions=False)


client = _client()


def test_app_error_uses_stable_envelope() -> None:
    response = client.get("/_test/app-error")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "IMAGE_TOO_BLURRY",
            "message": "The image is too blurry to analyze reliably.",
            "details": {"reason": "low_sharpness"},
        }
    }


def test_validation_error_uses_stable_envelope() -> None:
    response = client.post("/_test/echo", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "The request could not be validated."
    assert body["error"]["details"]["errors"]


def test_unexpected_error_hides_exception_text() -> None:
    response = client.get("/_test/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. The request was not processed.",
            "details": {},
        }
    }
    assert "RuntimeError" not in response.text
    assert "password" not in response.text
    assert "super-secret" not in response.text
    assert "Traceback" not in response.text


def test_successful_response_includes_request_id() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
