from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_seed_endpoint() -> None:
    with TestClient(app) as client:
        response = client.post("/api/analyze/seed", json={"top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_candidates"] >= 3
    assert payload["ranking"][0]["match_score"] >= payload["ranking"][-1]["match_score"]
