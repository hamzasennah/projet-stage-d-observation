from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI-Powered Resume Ranking System"
    api_prefix: str = "/api"
    project_root: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = project_root / "data"
    upload_dir: Path = data_dir / "uploads"
    database_path: Path = data_dir / "resume_ranking.sqlite3"
    default_criteria_path: Path = data_dir / "criteria" / "data_ai_stage.json"
    seed_manifest_path: Path = data_dir / "resumes" / "seed_manifest.json"
    allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "local").strip().lower()

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "").strip()


settings = Settings()

