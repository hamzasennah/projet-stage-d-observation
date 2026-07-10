import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import settings
from .models import ResumeRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS resumes (
    id TEXT PRIMARY KEY,
    candidate_name TEXT NOT NULL,
    title TEXT NOT NULL,
    focus TEXT NOT NULL,
    source_file TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criteria_id TEXT NOT NULL,
    criteria_title TEXT NOT NULL,
    job_title TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript(SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(settings.database_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert_resume(record: ResumeRecord) -> None:
    with connect() as con:
        con.execute(
            """
            INSERT INTO resumes (
                id, candidate_name, title, focus, source_file, raw_text, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                candidate_name = excluded.candidate_name,
                title = excluded.title,
                focus = excluded.focus,
                source_file = excluded.source_file,
                raw_text = excluded.raw_text,
                updated_at = excluded.updated_at
            """,
            (
                record.id,
                record.candidate_name,
                record.title,
                record.focus,
                record.source_file,
                record.raw_text,
                _now(),
            ),
        )


def list_resumes() -> list[ResumeRecord]:
    with connect() as con:
        rows = con.execute(
            """
            SELECT id, candidate_name, title, focus, source_file, raw_text
            FROM resumes
            ORDER BY id
            """
        ).fetchall()
    return [
        ResumeRecord(
            id=row["id"],
            candidate_name=row["candidate_name"],
            title=row["title"],
            focus=row["focus"],
            source_file=row["source_file"],
            raw_text=row["raw_text"],
        )
        for row in rows
    ]


def save_analysis(
    criteria_id: str,
    criteria_title: str,
    job_title: str,
    result: dict,
) -> int:
    with connect() as con:
        cursor = con.execute(
            """
            INSERT INTO analysis_runs (
                criteria_id, criteria_title, job_title, result_json, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                criteria_id,
                criteria_title,
                job_title,
                json.dumps(result, ensure_ascii=False),
                _now(),
            ),
        )
        return int(cursor.lastrowid)


def get_analysis(analysis_id: int) -> dict | None:
    with connect() as con:
        row = con.execute(
            "SELECT result_json FROM analysis_runs WHERE id = ?",
            (analysis_id,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["result_json"])


def database_exists(path: Path | None = None) -> bool:
    return (path or settings.database_path).exists()

