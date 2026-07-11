from ..models import CandidateAnalysis, CriterionResult, Evidence
from ..schemas import CandidateOutput, CriterionOutput, EvidenceOutput


def evidence_to_output(item: Evidence) -> EvidenceOutput:
    return EvidenceOutput(
        source=item.source,
        text=item.text,
        similarity=item.similarity,
    )


def criterion_to_output(item: CriterionResult) -> CriterionOutput:
    return CriterionOutput(
        label=item.label,
        weight=item.weight,
        score=item.score,
        matched_keywords=item.matched_keywords,
        missing_keywords=item.missing_keywords,
        evidence=[evidence_to_output(evidence) for evidence in item.evidence],
    )


def analysis_to_output(item: CandidateAnalysis) -> CandidateOutput:
    return CandidateOutput(
        candidate_id=item.candidate_id,
        candidate_name=item.candidate_name,
        resume_title=item.resume_title,
        match_score=item.match_score,
        summary=item.summary,
        pros=item.pros,
        cons=item.cons,
        criteria_breakdown=[
            criterion_to_output(criterion)
            for criterion in item.criteria_breakdown
        ],
        evidence=[evidence_to_output(evidence) for evidence in item.evidence],
    )

