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
    embedding_cache_path: Path = data_dir / "cache" / "ollama_embeddings.json"
    default_criteria_path: Path = data_dir / "criteria" / "spm_data_analyst_packaging.json"
    allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    @property
    def chroma_path(self) -> Path:
        return _path_from_env("CHROMA_PATH", self.data_dir / "chroma")

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "ollama").strip().lower()

    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")

    @property
    def ollama_generation_model(self) -> str:
        return os.getenv("OLLAMA_GENERATION_MODEL", "qwen2.5:7b").strip()

    @property
    def ollama_embedding_model(self) -> str:
        return os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b").strip()

    @property
    def rag_test_mode(self) -> bool:
        return os.getenv("RAG_TEST_MODE", "").strip().lower() in {"1", "true", "yes"}


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


settings = Settings()
