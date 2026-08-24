"""Phase 1: the application builds and both health routes answer."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

client = TestClient(create_app(Settings(app_env="development")))


def test_unversioned_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_versioned_health_returns_ok() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_404() -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "The requested resource was not found.",
            "details": {},
        }
    }


def test_cors_origins_accepts_comma_separated_string() -> None:
    settings = Settings(cors_origins="http://localhost:8081, http://localhost:8082")

    assert settings.cors_origins == ["http://localhost:8081", "http://localhost:8082"]
