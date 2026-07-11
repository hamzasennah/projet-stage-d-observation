from app.models import ResumeRecord
from app.schemas import CriteriaSheetInput
from app.services.criteria import load_default_criteria
from app.services.ranking import analyze_resume_records


def test_default_criteria_weights_are_valid() -> None:
    sheet = load_default_criteria()
    assert isinstance(sheet, CriteriaSheetInput)
    assert sum(criterion.weight for criterion in sheet.criteria) == 100


def test_uploaded_resume_ranking_returns_ordered_scores() -> None:
    sheet = load_default_criteria()
    records = [
        ResumeRecord(
            id="cv_bi",
            candidate_name="Candidat BI",
            title="CV importe - candidat_bi.pdf",
            focus="CV importe par l'utilisateur",
            source_file="test",
            raw_text=(
                "Data analyst avec Power BI, Excel, KPI dashboard, documentation, "
                "project management, french, english, Snowflake et Azure datalake."
            ),
        ),
        ResumeRecord(
            id="cv_python",
            candidate_name="Candidat Python",
            title="CV importe - candidat_python.pdf",
            focus="CV importe par l'utilisateur",
            source_file="test",
            raw_text="Python, machine learning, API, Git et SQL.",
        ),
        ResumeRecord(
            id="cv_general",
            candidate_name="Candidat General",
            title="CV importe - candidat_general.pdf",
            focus="CV importe par l'utilisateur",
            source_file="test",
            raw_text="Communication, formation generale et bureautique.",
        ),
    ]

    ranking = analyze_resume_records(sheet, records, top_k=3)

    assert len(ranking) == 3
    scores = [candidate.match_score for candidate in ranking]
    assert scores == sorted(scores, reverse=True)
    assert ranking[0].evidence
    assert ranking[0].criteria_breakdown
