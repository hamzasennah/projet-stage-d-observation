from __future__ import annotations

from uuid import uuid4

from ..config import settings
from ..models import CandidateAnalysis, CriterionResult, Evidence, ResumeRecord
from ..schemas import CriteriaSheetInput
from .chunker import split_text
from .criteria import criteria_query, validate_criteria_weights
from .gemini_client import get_gemini_client
from .tokenizer import keyword_in_text, matched_keywords, normalize_text
from .vector_store import ChromaResumeStore


def analyze_resume_records(
    sheet: CriteriaSheetInput,
    resumes: list[ResumeRecord],
    top_k: int = 5,
) -> list[CandidateAnalysis]:
    validate_criteria_weights(sheet)
    if not resumes:
        return []

    run_id = f"run_{uuid4().hex}"
    gemini = get_gemini_client()
    store = ChromaResumeStore()
    store.reset_run(run_id)

    query = criteria_query(sheet)
    query_embedding = gemini.embed_query(query)
    analyses: list[CandidateAnalysis] = []

    for resume in resumes:
        chunks = split_text(resume.raw_text)
        if not chunks:
            analyses.append(_empty_analysis(sheet, resume))
            continue

        chunk_embeddings = gemini.embed_documents(chunks)
        store.index_resume(run_id, resume, chunks, chunk_embeddings)
        retrieved = store.search_resume(
            run_id=run_id,
            resume_id=resume.id,
            query_embedding=query_embedding,
            top_k=top_k,
        )
        if settings.rag_test_mode:
            analyses.append(_keyword_analysis(sheet, resume, retrieved))
        else:
            analyses.append(_llm_analysis(sheet, resume, retrieved, gemini))

    analyses.sort(key=lambda item: item.match_score, reverse=True)
    return analyses


def _llm_analysis(
    sheet: CriteriaSheetInput,
    resume: ResumeRecord,
    evidence: list[Evidence],
    gemini,
) -> CandidateAnalysis:
    payload = gemini.generate_json(_analysis_prompt(sheet, resume, evidence))
    breakdown = _criteria_from_payload(sheet, payload, evidence)
    score = _number(payload.get("match_score"), default=sum(item.score for item in breakdown))

    return CandidateAnalysis(
        candidate_id=resume.id,
        candidate_name=str(payload.get("candidate_name") or resume.candidate_name),
        resume_title=resume.title,
        match_score=_clamp(score, 0, 100),
        summary=str(payload.get("summary") or "Analyse Gemini sans resume exploitable."),
        pros=_string_list(payload.get("pros"))[:5],
        cons=_string_list(payload.get("cons"))[:5],
        criteria_breakdown=breakdown,
        evidence=evidence,
    )


def _analysis_prompt(
    sheet: CriteriaSheetInput,
    resume: ResumeRecord,
    evidence: list[Evidence],
) -> str:
    criteria_lines = "\n".join(
        (
            f"- {criterion.label} ({criterion.weight} pts): {criterion.description}. "
            f"Mots-cles indicatifs: {', '.join(criterion.keywords)}"
        )
        for criterion in sheet.criteria
    )
    evidence_text = "\n\n".join(
        f"[PREUVE {index}] source={item.source} similarite={item.similarity}\n{item.text}"
        for index, item in enumerate(evidence, start=1)
    )

    return f"""
Tu es un recruteur technique senior. Tu dois classer un CV par rapport a une fiche de poste.
Utilise uniquement les preuves fournies ci-dessous. N'invente aucune experience.

FICHE DE POSTE / CRITERES:
Titre: {sheet.job_title}
Description: {sheet.job_description}
Competences obligatoires: {', '.join(sheet.required_skills)}
Competences souhaitees: {', '.join(sheet.preferred_skills)}

CRITERES PONDERES:
{criteria_lines}

CV A ANALYSER:
Candidat: {resume.candidate_name}
CV: {resume.title}
Categorie/source: {resume.focus}

PREUVES RAG RECUPEREES DEPUIS CHROMADB:
{evidence_text}

Retourne uniquement un JSON valide avec cette structure:
{{
  "candidate_name": "{resume.candidate_name}",
  "match_score": nombre entre 0 et 100,
  "summary": "resume court et concret",
  "pros": ["point fort justifie", "point fort justifie"],
  "cons": ["faiblesse ou manque justifie", "faiblesse ou manque justifie"],
  "criteria_breakdown": [
    {{
      "label": "nom exact du critere",
      "score": nombre entre 0 et le poids du critere,
      "matched_keywords": ["competence trouvee"],
      "missing_keywords": ["competence absente ou non prouvee"]
    }}
  ]
}}
"""


def _criteria_from_payload(
    sheet: CriteriaSheetInput,
    payload: dict,
    evidence: list[Evidence],
) -> list[CriterionResult]:
    rows = payload.get("criteria_breakdown") if isinstance(payload, dict) else []
    rows = rows if isinstance(rows, list) else []
    by_label = {
        str(row.get("label", "")).strip().lower(): row
        for row in rows
        if isinstance(row, dict)
    }
    results: list[CriterionResult] = []
    for criterion in sheet.criteria:
        row = by_label.get(criterion.label.lower(), {})
        score = _clamp(_number(row.get("score"), default=0), 0, criterion.weight)
        results.append(
            CriterionResult(
                label=criterion.label,
                weight=criterion.weight,
                score=round(score, 2),
                matched_keywords=_string_list(row.get("matched_keywords")),
                missing_keywords=_string_list(row.get("missing_keywords")),
                evidence=evidence[: max(criterion.minimum_evidence, 1)],
            )
        )
    return results


def _keyword_analysis(
    sheet: CriteriaSheetInput,
    resume: ResumeRecord,
    evidence: list[Evidence],
) -> CandidateAnalysis:
    normalized_text = normalize_text(resume.raw_text)
    breakdown: list[CriterionResult] = []
    total = 0.0
    for criterion in sheet.criteria:
        matched = matched_keywords(criterion.keywords, normalized_text)
        missing = [keyword for keyword in criterion.keywords if keyword not in matched]
        coverage = len(matched) / len(criterion.keywords) if criterion.keywords else 0
        score = round(criterion.weight * coverage, 2)
        total += score
        breakdown.append(
            CriterionResult(
                label=criterion.label,
                weight=criterion.weight,
                score=score,
                matched_keywords=matched,
                missing_keywords=missing,
                evidence=evidence[: max(criterion.minimum_evidence, 1)],
            )
        )
    return CandidateAnalysis(
        candidate_id=resume.id,
        candidate_name=resume.candidate_name,
        resume_title=resume.title,
        match_score=round(_clamp(total, 0, 100), 2),
        summary=f"Analyse de test RAG/Chroma pour {resume.candidate_name}.",
        pros=_pros(breakdown),
        cons=_cons(breakdown),
        criteria_breakdown=breakdown,
        evidence=evidence,
    )


def _empty_analysis(sheet: CriteriaSheetInput, resume: ResumeRecord) -> CandidateAnalysis:
    return CandidateAnalysis(
        candidate_id=resume.id,
        candidate_name=resume.candidate_name,
        resume_title=resume.title,
        match_score=0,
        summary="CV vide ou impossible a extraire.",
        pros=[],
        cons=["Aucun texte exploitable n'a ete extrait du CV."],
        criteria_breakdown=[
            CriterionResult(label=item.label, weight=item.weight, score=0)
            for item in sheet.criteria
        ],
        evidence=[],
    )


def _pros(breakdown: list[CriterionResult]) -> list[str]:
    pros = []
    for criterion in breakdown:
        ratio = criterion.score / criterion.weight if criterion.weight else 0
        if ratio >= 0.65 and criterion.matched_keywords:
            pros.append(
                f"{criterion.label}: {', '.join(criterion.matched_keywords[:4])}."
            )
    return pros[:4] or ["Aucun point fort majeur n'a depasse le seuil de validation."]


def _cons(breakdown: list[CriterionResult]) -> list[str]:
    cons = []
    for criterion in breakdown:
        ratio = criterion.score / criterion.weight if criterion.weight else 0
        if ratio < 0.5:
            missing = ", ".join(criterion.missing_keywords[:4]) or "preuves insuffisantes"
            cons.append(f"{criterion.label}: elements faibles ou absents ({missing}).")
    return cons[:4] or ["Pas de faiblesse critique detectee selon la fiche fournie."]


def _string_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _number(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return round(max(minimum, min(maximum, value)), 2)
