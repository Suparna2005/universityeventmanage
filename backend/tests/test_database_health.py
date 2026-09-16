from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_database_health_returns_a_clear_contract() -> None:
    response = client.get("/api/health/database")
    assert response.status_code in {200, 503}
    body = response.json()
    assert set(body) == {"status", "message"}
    assert body["status"] in {"success", "error"}
