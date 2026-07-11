from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from ..database import upsert_resume
from ..models import ResumeRecord
from .chunker import split_text
from .gemini_client import get_gemini_client
from .vector_store import ChromaResumeStore


KAGGLE_NAMESPACE = "kaggle_resume_archive"


@dataclass
class KaggleImportStats:
    imported: int = 0
    indexed_chunks: int = 0
    skipped: int = 0


def import_kaggle_archive(
    archive_path: str | Path,
    *,
    limit: int | None = None,
    categories: set[str] | None = None,
    index_chroma: bool = True,
    batch_size: int = 24,
) -> KaggleImportStats:
    archive = Path(archive_path)
    stats = KaggleImportStats()
    gemini = get_gemini_client() if index_chroma else None
    store = ChromaResumeStore() if index_chroma else None

    with ZipFile(archive) as zip_file:
        with zip_file.open("Resume/Resume.csv") as csv_file:
            wrapper = (line.decode("utf-8", errors="replace") for line in csv_file)
            reader = csv.DictReader(wrapper)
            pending: list[tuple[ResumeRecord, list[str]]] = []
            for row in reader:
                category = (row.get("Category") or "UNKNOWN").strip()
                if categories and category.upper() not in categories:
                    stats.skipped += 1
                    continue
                text = (row.get("Resume_str") or "").strip()
                resume_id = (row.get("ID") or "").strip()
                if not resume_id or not text:
                    stats.skipped += 1
                    continue

                record = ResumeRecord(
                    id=f"kaggle_{resume_id}",
                    candidate_name=f"Kaggle CV {resume_id}",
                    title=f"{category} resume {resume_id}",
                    focus=category,
                    source_file=f"{archive.name}::Resume/Resume.csv#{resume_id}",
                    raw_text=text,
                )
                upsert_resume(record)
                stats.imported += 1

                if index_chroma:
                    chunks = split_text(text)
                    pending.append((record, chunks))
                    if len(pending) >= batch_size:
                        stats.indexed_chunks += _index_batch(pending, gemini, store)
                        pending = []

                if limit and stats.imported >= limit:
                    break

            if pending:
                stats.indexed_chunks += _index_batch(pending, gemini, store)

    return stats


def _index_batch(records: list[tuple[ResumeRecord, list[str]]], gemini, store) -> int:
    indexed = 0
    for record, chunks in records:
        if not chunks:
            continue
        embeddings = gemini.embed_documents(chunks)
        store.index_resume(KAGGLE_NAMESPACE, record, chunks, embeddings)
        indexed += len(chunks)
    return indexed

