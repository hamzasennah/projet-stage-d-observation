from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI-Powered Resume Ranking System"
    api_prefix: str = "/api"
    project_root: Path = PROJECT_ROOT
    data_dir: Path = project_root / "data"
    upload_dir: Path = data_dir / "uploads"
    chroma_path: Path = data_dir / "chroma"
    embedding_cache_path: Path = data_dir / "cache" / "gemini_embeddings.json"
    default_criteria_path: Path = data_dir / "criteria" / "spm_data_analyst_packaging.json"
    allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "gemini").strip().lower()

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "").strip()

    @property
    def gemini_generation_model(self) -> str:
        return os.getenv("GEMINI_GENERATION_MODEL", "gemini-flash-lite-latest").strip()

    @property
    def gemini_fallback_model(self) -> str:
        return os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-latest").strip()

    @property
    def gemini_embedding_model(self) -> str:
        return os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004").strip()

    @property
    def gemini_embedding_fallback_model(self) -> str:
        return os.getenv("GEMINI_EMBEDDING_FALLBACK_MODEL", "gemini-embedding-001").strip()

    @property
    def rag_test_mode(self) -> bool:
        return os.getenv("RAG_TEST_MODE", "").strip().lower() in {"1", "true", "yes"}


settings = Settings()
