import json
from pathlib import Path

from ..config import settings
from ..schemas import CriteriaSheetInput


def load_default_criteria() -> CriteriaSheetInput:
    return load_criteria(settings.default_criteria_path)


def load_criteria(path: str | Path) -> CriteriaSheetInput:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    sheet = CriteriaSheetInput(**data)
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

