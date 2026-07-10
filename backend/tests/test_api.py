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


def test_analyze_documents_endpoint() -> None:
    criteria = (
        "Fiche de test stage Data IA RAG. Competences demandees: Python, "
        "machine learning, RAG, embeddings, API, SQL, Git, FastAPI et React."
    )
    cv_1 = (
        "Hamza Sennah. Python, machine learning, RAG, embeddings, API FastAPI, "
        "SQL, Git, ObesoScan, Streamlit et SHAP."
    )
    cv_2 = "Candidat junior. Excel, communication et formation generale."

    files = [
        ("criteria_file", ("fiche_test.txt", criteria.encode("utf-8"), "text/plain")),
        ("files", ("cv_data.txt", cv_1.encode("utf-8"), "text/plain")),
        ("files", ("cv_general.txt", cv_2.encode("utf-8"), "text/plain")),
    ]
    with TestClient(app) as client:
        response = client.post("/api/analyze/documents", files=files, data={"top_k": "3"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_candidates"] == 2
    assert payload["ranking"][0]["resume_title"] == "CV importe - cv_data.txt"
    assert payload["ranking"][0]["match_score"] > payload["ranking"][1]["match_score"]
