from app.schemas import CriteriaSheetInput
from app.services.criteria import load_default_criteria
from app.services.ranking import analyze_resume_records
from app.services.seed_loader import load_seed_records


def test_default_criteria_weights_are_valid() -> None:
    sheet = load_default_criteria()
    assert isinstance(sheet, CriteriaSheetInput)
    assert sum(criterion.weight for criterion in sheet.criteria) == 100


def test_seed_ranking_returns_ordered_scores() -> None:
    sheet = load_default_criteria()
    records = load_seed_records()

    ranking = analyze_resume_records(sheet, records, top_k=3)

    assert len(ranking) >= 3
    scores = [candidate.match_score for candidate in ranking]
    assert scores == sorted(scores, reverse=True)
    assert ranking[0].evidence
    assert ranking[0].criteria_breakdown

