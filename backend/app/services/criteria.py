import json
from pathlib import Path
from uuid import uuid4

from ..config import settings
from ..schemas import CriteriaSheetInput, CriterionInput
from .tokenizer import matched_keywords


CRITERIA_CATALOG: dict[str, dict[str, object]] = {
    "Competences obligatoires": {
        "weight": 40,
        "description": "Competences directement demandees par la fiche de test.",
        "keywords": [
            "python",
            "machine learning",
            "deep learning",
            "ia",
            "rag",
            "embedding",
            "embeddings",
            "api",
            "fastapi",
            "sql",
            "git",
            "github",
            "base de donnees",
            "chroma",
            "chromadb",
        ],
    },
    "Experience et projets appliques": {
        "weight": 25,
        "description": "Realisations, projets et preuves d'application pratique.",
        "keywords": [
            "projet",
            "pipeline",
            "pipeline de donnees",
            "agroshield",
            "obesoscan",
            "cnn",
            "streamlit",
            "shap",
            "power bi",
            "ci/cd",
            "visualisation",
            "simulation",
        ],
    },
    "Competences souhaitees": {
        "weight": 20,
        "description": "Competences qui ameliorent l'adequation au poste.",
        "keywords": [
            "react",
            "typescript",
            "javascript",
            "html",
            "css",
            "excel",
            "power query",
            "jira",
            "projectlibre",
            "documentation",
            "tests",
            "frontend",
            "backend",
        ],
    },
    "Coherence globale du profil": {
        "weight": 15,
        "description": "Formation, rigueur, langues et alignement general avec le poste.",
        "keywords": [
            "ecole centrale casablanca",
            "ingenieur",
            "mathematiques",
            "mathematiques appliquees",
            "algorithmique",
            "rigoureux",
            "resolution de problemes",
            "innovation",
            "francais",
            "anglais",
        ],
    },
}


def load_default_criteria() -> CriteriaSheetInput:
    return load_criteria(settings.default_criteria_path)


def load_criteria(path: str | Path) -> CriteriaSheetInput:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    sheet = CriteriaSheetInput(**data)
    validate_criteria_weights(sheet)
    return sheet


def criteria_from_document_text(text: str, source_name: str) -> CriteriaSheetInput:
    """Build a scoring sheet from an uploaded criteria document.

    The full document remains the reference query for retrieval. Keywords are
    extracted from a controlled catalog so the scoring stays explainable and
    deterministic without requiring an external LLM key.
    """

    clean = " ".join(text.split())
    if len(clean) < 30:
        raise ValueError("La fiche de test ne contient pas assez de texte exploitable.")

    criteria: list[CriterionInput] = []
    required_skills: list[str] = []
    preferred_skills: list[str] = []

    for label, spec in CRITERIA_CATALOG.items():
        catalog_keywords = list(spec["keywords"])  # type: ignore[index]
        found = matched_keywords(catalog_keywords, clean)
        if not found:
            found = catalog_keywords[:4]
        if label == "Competences obligatoires":
            required_skills = found
        elif label == "Competences souhaitees":
            preferred_skills = found

        criteria.append(
            CriterionInput(
                label=label,
                weight=float(spec["weight"]),  # type: ignore[index]
                description=str(spec["description"]),
                keywords=found,
                minimum_evidence=2,
            )
        )

    title = _document_title(clean, source_name)
    sheet = CriteriaSheetInput(
        id=f"uploaded-{uuid4().hex[:10]}",
        title=f"Fiche importee - {source_name}",
        job_title=title,
        job_description=clean,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        criteria=criteria,
        red_flags=["aucune experience technique", "pas de projet", "pas de python"],
    )
    validate_criteria_weights(sheet)
    return sheet


def validate_criteria_weights(sheet: CriteriaSheetInput) -> None:
    if not sheet.criteria:
        raise ValueError("La fiche de test doit contenir au moins un critere.")
    total = sum(item.weight for item in sheet.criteria)
    if abs(total - 100) > 0.01:
        raise ValueError(f"La somme des poids doit etre egale a 100, pas {total}.")


def criteria_query(sheet: CriteriaSheetInput) -> str:
    keywords: list[str] = []
    for criterion in sheet.criteria:
        keywords.extend(criterion.keywords)
    return " ".join(
        [
            sheet.job_title,
            sheet.job_description,
            " ".join(sheet.required_skills),
            " ".join(sheet.preferred_skills),
            " ".join(keywords),
        ]
    )


def _document_title(text: str, source_name: str) -> str:
    first_sentence = text.split(".")[0].strip()
    if 8 <= len(first_sentence) <= 90:
        return first_sentence
    stem = Path(source_name).stem.replace("_", " ").replace("-", " ").strip()
    return stem or "Fiche de test importee"
