from contextlib import asynccontextmanager
from hashlib import sha1
import json
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import get_analysis, init_db, list_resumes, save_analysis
from .models import ResumeRecord
from .schemas import (
    AnalyzeSeedRequest,
    AnalyzeTextRequest,
    CriteriaSheetInput,
    RankingResponse,
    ResumeOutput,
)
from .services.criteria import load_default_criteria, validate_criteria_weights
from .services.parser import SUPPORTED_EXTENSIONS, extract_text
from .services.rag_engine import analysis_to_output, ranking_response_to_dict
from .services.ranking import analyze_resume_records, text_resumes_to_records
from .services.seed_loader import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_database()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Systeme de classement de CV avec recherche RAG locale et scoring explicable.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Resume Ranking RAG API is running",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }


@app.get(f"{settings.api_prefix}/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get(f"{settings.api_prefix}/criteria/default", response_model=CriteriaSheetInput)
def default_criteria() -> CriteriaSheetInput:
    return load_default_criteria()


@app.get(f"{settings.api_prefix}/resumes/seed", response_model=list[ResumeOutput])
def seed_resumes() -> list[ResumeOutput]:
    return [
        ResumeOutput(
            id=record.id,
            candidate_name=record.candidate_name,
            title=record.title,
            focus=record.focus,
            source_file=record.source_file,
        )
        for record in list_resumes()
    ]


@app.post(f"{settings.api_prefix}/resumes/reseed")
def reseed() -> dict[str, int]:
    init_db()
    count = seed_database()
    return {"seeded": count}


@app.post(f"{settings.api_prefix}/analyze/seed", response_model=RankingResponse)
def analyze_seed(request: AnalyzeSeedRequest) -> RankingResponse:
    sheet = request.criteria_sheet or load_default_criteria()
    validate_criteria_weights(sheet)
    analyses = analyze_resume_records(sheet, list_resumes(), top_k=request.top_k)
    response = _build_response(sheet, analyses)
    analysis_id = save_analysis(
        criteria_id=sheet.id,
        criteria_title=sheet.title,
        job_title=sheet.job_title,
        result=ranking_response_to_dict(response),
    )
    response.analysis_id = analysis_id
    return response


@app.post(f"{settings.api_prefix}/analyze/text", response_model=RankingResponse)
def analyze_text(request: AnalyzeTextRequest) -> RankingResponse:
    validate_criteria_weights(request.criteria_sheet)
    records = text_resumes_to_records(request.resumes)
    analyses = analyze_resume_records(
        request.criteria_sheet,
        records,
        top_k=request.top_k,
    )
    return _build_response(request.criteria_sheet, analyses)


@app.post(f"{settings.api_prefix}/analyze/upload", response_model=RankingResponse)
async def analyze_upload(
    files: Annotated[list[UploadFile], File(...)],
    job_description: Annotated[str | None, Form()] = None,
    criteria_json: Annotated[str | None, Form()] = None,
    top_k: Annotated[int, Form(ge=1, le=20)] = 5,
) -> RankingResponse:
    sheet = _sheet_from_upload(job_description, criteria_json)
    validate_criteria_weights(sheet)
    records: list[ResumeRecord] = []

    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Format non supporte pour {upload.filename}.",
            )
        saved_path = await _save_upload(upload)
        text = extract_text(saved_path)
        records.append(
            ResumeRecord(
                id=_record_id(upload.filename or saved_path.name),
                candidate_name=Path(upload.filename or saved_path.name).stem,
                title=f"CV importe - {upload.filename}",
                focus="CV importe par l'utilisateur",
                source_file=str(saved_path),
                raw_text=text,
            )
        )

    analyses = analyze_resume_records(sheet, records, top_k=top_k)
    return _build_response(sheet, analyses)


@app.get(f"{settings.api_prefix}/analyses/{{analysis_id}}")
def analysis_run(analysis_id: int) -> dict:
    result = get_analysis(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analyse introuvable.")
    return result


def _build_response(sheet: CriteriaSheetInput, analyses) -> RankingResponse:
    return RankingResponse(
        criteria_id=sheet.id,
        criteria_title=sheet.title,
        job_title=sheet.job_title,
        total_candidates=len(analyses),
        ranking=[analysis_to_output(item) for item in analyses],
    )


def _sheet_from_upload(
    job_description: str | None,
    criteria_json: str | None,
) -> CriteriaSheetInput:
    if criteria_json:
        try:
            payload = json.loads(criteria_json)
            return CriteriaSheetInput(**payload)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"criteria_json invalide: {exc}",
            ) from exc
    sheet = load_default_criteria()
    if job_description:
        sheet.job_description = job_description
    return sheet


async def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "resume.txt").suffix.lower()
    target = settings.upload_dir / f"{_record_id(upload.filename or 'resume')}{suffix}"
    content = await upload.read()
    target.write_bytes(content)
    return target


def _record_id(value: str) -> str:
    digest = sha1(value.encode("utf-8")).hexdigest()[:12]
    stem = Path(value).stem.lower().replace(" ", "_")[:30] or "resume"
    return f"{stem}_{digest}"
