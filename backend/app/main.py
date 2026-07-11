from hashlib import sha1
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import ResumeRecord
from .schemas import (
    CriteriaSheetInput,
    RankingResponse,
)
from .services.criteria import (
    criteria_from_document_text,
    load_default_criteria,
    validate_criteria_weights,
)
from .services.gemini_client import GeminiConfigurationError, GeminiQuotaError
from .services.parser import SUPPORTED_EXTENSIONS, extract_text
from .services.rag_engine import analysis_to_output
from .services.ranking import analyze_resume_records


app = FastAPI(
    title=settings.app_name,
    description="Systeme de classement de CV avec RAG Gemini, embeddings et ChromaDB.",
    version="1.0.0",
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


@app.post(f"{settings.api_prefix}/analyze/documents", response_model=RankingResponse)
async def analyze_documents(
    criteria_file: Annotated[UploadFile, File(...)],
    files: Annotated[list[UploadFile], File(...)],
    top_k: Annotated[int, Form(ge=1, le=20)] = 5,
) -> RankingResponse:
    criteria_path = await _save_upload(criteria_file, prefix="criteria_")
    criteria_text = extract_text(criteria_path)
    try:
        sheet = criteria_from_document_text(
            criteria_text,
            criteria_file.filename or criteria_path.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    records = [await _upload_to_resume_record(upload) for upload in files]
    analyses = _run_rag_analysis(sheet, records, top_k=top_k)
    return _build_response(sheet, analyses)


def _build_response(sheet: CriteriaSheetInput, analyses) -> RankingResponse:
    return RankingResponse(
        criteria_id=sheet.id,
        criteria_title=sheet.title,
        job_title=sheet.job_title,
        total_candidates=len(analyses),
        ranking=[analysis_to_output(item) for item in analyses],
    )


def _run_rag_analysis(
    sheet: CriteriaSheetInput,
    records: list[ResumeRecord],
    top_k: int,
):
    try:
        return analyze_resume_records(sheet, records, top_k=top_k)
    except GeminiQuotaError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except GeminiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


async def _upload_to_resume_record(upload: UploadFile) -> ResumeRecord:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporte pour {upload.filename}.",
        )
    saved_path = await _save_upload(upload, prefix="resume_")
    text = extract_text(saved_path)
    return ResumeRecord(
        id=_record_id(upload.filename or saved_path.name),
        candidate_name=Path(upload.filename or saved_path.name).stem,
        title=f"CV importe - {upload.filename}",
        focus="CV importe par l'utilisateur",
        source_file=str(saved_path),
        raw_text=text,
    )


async def _save_upload(upload: UploadFile, prefix: str = "") -> Path:
    suffix = Path(upload.filename or "resume.txt").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporte pour {upload.filename}.",
        )
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    target = settings.upload_dir / f"{prefix}{_record_id(upload.filename or 'document')}{suffix}"
    content = await upload.read()
    target.write_bytes(content)
    return target


def _record_id(value: str) -> str:
    digest = sha1(value.encode("utf-8")).hexdigest()[:12]
    stem = Path(value).stem.lower().replace(" ", "_")[:30] or "resume"
    return f"{stem}_{digest}"
