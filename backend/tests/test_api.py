from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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


def test_analyze_documents_accepts_larger_cv_batches() -> None:
    criteria = (
        "Fiche de poste Data Analyst. Competences demandees: Power BI, Excel, "
        "SQL, dashboards, documentation, project management et anglais."
    )
    files = [
        ("criteria_file", ("fiche_test.txt", criteria.encode("utf-8"), "text/plain")),
    ]
    for index in range(12):
        cv_text = (
            f"Candidat {index}. Data analyst avec Power BI, Excel, SQL, "
            "dashboards KPI, documentation et gestion projet."
        )
        files.append(
            (
                "files",
                (f"cv_batch_{index:02d}.txt", cv_text.encode("utf-8"), "text/plain"),
            )
        )

    with TestClient(app) as client:
        response = client.post("/api/analyze/documents", files=files, data={"top_k": "2"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_candidates"] == 12
    assert len(payload["ranking"]) == 12


def test_analyze_documents_reports_missing_ollama(monkeypatch) -> None:
    monkeypatch.delenv("RAG_TEST_MODE", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9")

    files = [
        (
            "criteria_file",
            (
                "fiche_test.txt",
                b"Fiche de poste Data Analyst. Competences: Python, SQL, Power BI.",
                "text/plain",
            ),
        ),
        (
            "files",
            (
                "cv_data.txt",
                b"Candidat Data Analyst avec Python, SQL et Power BI.",
                "text/plain",
            ),
        ),
    ]

    with TestClient(app) as client:
        response = client.post("/api/analyze/documents", files=files, data={"top_k": "2"})

    assert response.status_code == 503
    assert "Ollama" in response.json()["detail"]
