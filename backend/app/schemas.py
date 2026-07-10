from pydantic import BaseModel, Field


class CriterionInput(BaseModel):
    label: str = Field(..., min_length=2)
    weight: float = Field(..., ge=0, le=100)
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    minimum_evidence: int = Field(default=1, ge=0, le=10)


class CriteriaSheetInput(BaseModel):
    id: str = "custom"
    title: str = "Fiche de test personnalisee"
    job_title: str
    job_description: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    criteria: list[CriterionInput]
    red_flags: list[str] = Field(default_factory=list)


class AnalyzeSeedRequest(BaseModel):
    criteria_sheet: CriteriaSheetInput | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class AnalyzeTextResume(BaseModel):
    candidate_name: str
    title: str
    raw_text: str
    focus: str = ""


class AnalyzeTextRequest(BaseModel):
    criteria_sheet: CriteriaSheetInput
    resumes: list[AnalyzeTextResume]
    top_k: int = Field(default=5, ge=1, le=20)


class EvidenceOutput(BaseModel):
    source: str
    text: str
    similarity: float


class CriterionOutput(BaseModel):
    label: str
    weight: float
    score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    evidence: list[EvidenceOutput]


class CandidateOutput(BaseModel):
    candidate_id: str
    candidate_name: str
    resume_title: str
    match_score: float
    summary: str
    pros: list[str]
    cons: list[str]
    criteria_breakdown: list[CriterionOutput]
    evidence: list[EvidenceOutput]


class RankingResponse(BaseModel):
    criteria_id: str
    criteria_title: str
    job_title: str
    total_candidates: int
    ranking: list[CandidateOutput]
    analysis_id: int | None = None


class ResumeOutput(BaseModel):
    id: str
    candidate_name: str
    title: str
    focus: str
    source_file: str

