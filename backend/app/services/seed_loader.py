import json
from pathlib import Path

from ..config import settings
from ..database import upsert_resume
from ..models import ResumeRecord


def load_seed_records() -> list[ResumeRecord]:
    manifest_path = settings.seed_manifest_path
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_dir = manifest_path.parent
    records: list[ResumeRecord] = []
    for item in manifest.get("resumes", []):
        source_file = item["source_file"]
        raw_text = (base_dir / "seed" / source_file).read_text(encoding="utf-8")
        records.append(
            ResumeRecord(
                id=item["id"],
                candidate_name=item["candidate_name"],
                title=item["title"],
                focus=item.get("focus", ""),
                source_file=str(Path("data") / "resumes" / "seed" / source_file),
                raw_text=raw_text,
            )
        )
    return records


def seed_database() -> int:
    records = load_seed_records()
    for record in records:
        upsert_resume(record)
    return len(records)

