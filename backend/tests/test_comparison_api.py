"""Test for POST /api/v1/comparison HTTP API endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_comparison_endpoint() -> None:
    payload = {
        "products": [
            {
                "product_id": "p1",
                "product_name": "Brand A",
                "values": {"SUGAR": {"value": "10", "unit": "g"}},
            },
            {
                "product_id": "p2",
                "product_name": "Brand B",
                "values": {"SUGAR": {"value": "4", "unit": "g"}},
            },
        ],
        "priorities": [{"priority": "LOWER_SUGAR", "weight": 1}],
    }

    response = client.post("/api/v1/comparison", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["winner"] == "Brand B"
    assert len(data["ranking"]) == 2
    assert data["ranking"][0]["product_id"] == "p2"
