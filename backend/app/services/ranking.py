from hashlib import sha1

from ..models import CandidateAnalysis, CriterionResult, Evidence, ResumeRecord
from ..schemas import AnalyzeTextResume, CriteriaSheetInput
from .chunker import split_text
from .criteria import criteria_query, validate_criteria_weights
from .tokenizer import keyword_in_text, matched_keywords, normalize_text
from .vector_store import TfidfVectorStore


def analyze_resume_records(
    sheet: CriteriaSheetInput,
    resumes: list[ResumeRecord],
    top_k: int = 5,
) -> list[CandidateAnalysis]:
    validate_criteria_weights(sheet)
    store = TfidfVectorStore()
    chunks_by_resume: dict[str, list[str]] = {}

    for resume in resumes:
        chunks = split_text(resume.raw_text)
        chunks_by_resume[resume.id] = chunks
        store.index(resume.id, chunks)

    query = criteria_query(sheet)
    analyses = [
        _score_resume(sheet, resume, chunks_by_resume[resume.id], store, query, top_k)
        for resume in resumes
    ]
    analyses.sort(key=lambda item: item.match_score, reverse=True)
    return analyses


def text_resumes_to_records(resumes: list[AnalyzeTextResume]) -> list[ResumeRecord]:
    records: list[ResumeRecord] = []
    for index, resume in enumerate(resumes, start=1):
        digest = sha1(f"{resume.candidate_name}-{resume.title}-{index}".encode()).hexdigest()[:10]
        records.append(
            ResumeRecord(
                id=f"uploaded_text_{digest}",
                candidate_name=resume.candidate_name,
                title=resume.title,
                focus=resume.focus,
                source_file="text-payload",
                raw_text=resume.raw_text,
            )
        )
    return records


def _score_resume(
    sheet: CriteriaSheetInput,
    resume: ResumeRecord,
    chunks: list[str],
    store: TfidfVectorStore,
    query: str,
    top_k: int,
) -> CandidateAnalysis:
    retrieved = store.search(resume.id, query, top_k=top_k)
    full_text = resume.raw_text
    normalized_text = normalize_text(full_text)

    breakdown: list[CriterionResult] = []
    score = 0.0
    for criterion in sheet.criteria:
        matched = matched_keywords(criterion.keywords, normalized_text)
        missing = [keyword for keyword in criterion.keywords if keyword not in matched]
        coverage = len(matched) / len(criterion.keywords) if criterion.keywords else 0
        criterion_score = round(criterion.weight * coverage, 2)
        score += criterion_score
        breakdown.append(
            CriterionResult(
                label=criterion.label,
                weight=criterion.weight,
                score=criterion_score,
                matched_keywords=matched,
                missing_keywords=missing,
                evidence=_criterion_evidence(chunks, matched, retrieved, resume.id),
            )
        )

    penalty = _red_flag_penalty(sheet.red_flags, normalized_text)
    final_score = max(0.0, min(100.0, round(score - penalty, 2)))
    evidence = _dedupe_evidence(
        [item for criterion in breakdown for item in criterion.evidence] + retrieved
    )[:top_k]

    return CandidateAnalysis(
        candidate_id=resume.id,
        candidate_name=resume.candidate_name,
        resume_title=resume.title,
        match_score=final_score,
        summary=_summary(resume, final_score, breakdown),
        pros=_pros(breakdown),
        cons=_cons(breakdown, penalty),
        criteria_breakdown=breakdown,
        evidence=evidence,
    )


def _criterion_evidence(
    chunks: list[str],
    matched: list[str],
    retrieved: list[Evidence],
    resume_id: str,
) -> list[Evidence]:
    if not matched:
        return retrieved[:1]

    selected: list[Evidence] = []
    for index, chunk in enumerate(chunks, start=1):
        if any(keyword_in_text(keyword, chunk) for keyword in matched):
            selected.append(
                Evidence(
                    source=f"{resume_id}_chunk_{index}",
                    text=chunk,
                    similarity=0.0,
                )
            )
        if len(selected) == 2:
            break
    return selected or retrieved[:1]


def _red_flag_penalty(red_flags: list[str], normalized_text: str) -> float:
    penalty = 0.0
    for red_flag in red_flags:
        if keyword_in_text(red_flag, normalized_text):
            penalty += 5.0
    return penalty


def _summary(
    resume: ResumeRecord,
    score: float,
    breakdown: list[CriterionResult],
) -> str:
    best = sorted(breakdown, key=lambda item: item.score / max(item.weight, 1), reverse=True)
    best_labels = ", ".join(item.label.lower() for item in best[:2])
    focus = f" Axe principal: {resume.focus}." if resume.focus else ""
    return (
        f"Profil {resume.candidate_name} evalue a {score:.0f}/100. "
        f"Les meilleurs signaux concernent {best_labels}.{focus}"
    )


def _pros(breakdown: list[CriterionResult]) -> list[str]:
    pros: list[str] = []
    for criterion in breakdown:
        ratio = criterion.score / criterion.weight if criterion.weight else 0
        if ratio >= 0.65 and criterion.matched_keywords:
            keywords = ", ".join(criterion.matched_keywords[:4])
            pros.append(f"{criterion.label}: preuves trouvees sur {keywords}.")
    return pros[:4] or ["Aucun point fort majeur n'a depasse le seuil de validation."]


def _cons(breakdown: list[CriterionResult], penalty: float) -> list[str]:
    cons: list[str] = []
    for criterion in breakdown:
        ratio = criterion.score / criterion.weight if criterion.weight else 0
        if ratio < 0.5:
            missing = ", ".join(criterion.missing_keywords[:4]) or "preuves insuffisantes"
            cons.append(f"{criterion.label}: elements manquants ou faibles ({missing}).")
    if penalty:
        cons.append(f"Penalite appliquee pour signaux de risque: -{penalty:.0f} points.")
    return cons[:4] or ["Pas de faiblesse critique detectee selon la fiche fournie."]


def _dedupe_evidence(items: list[Evidence]) -> list[Evidence]:
    seen: set[str] = set()
    deduped: list[Evidence] = []
    for item in items:
        key = normalize_text(item.text)[:180]
        if key in seen or not key:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped

