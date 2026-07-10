from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResumeRecord:
    id: str
    candidate_name: str
    title: str
    focus: str
    source_file: str
    raw_text: str


@dataclass(frozen=True)
class Evidence:
    source: str
    text: str
    similarity: float = 0.0


@dataclass
class CriterionResult:
    label: str
    weight: float
    score: float
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class CandidateAnalysis:
    candidate_id: str
    candidate_name: str
    resume_title: str
    match_score: float
    summary: str
    pros: list[str]
    cons: list[str]
    criteria_breakdown: list[CriterionResult]
    evidence: list[Evidence]

