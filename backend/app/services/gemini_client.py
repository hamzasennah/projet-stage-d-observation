from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

from ..config import settings
from .tokenizer import tokenize


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiClient:
    _max_retry_attempts = 4

    def __init__(self) -> None:
        if settings.llm_provider != "gemini":
            raise GeminiConfigurationError("LLM_PROVIDER doit etre defini a 'gemini'.")
        if not settings.gemini_api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY est manquante dans l'environnement.")

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise GeminiConfigurationError(
                "Le package google-genai est manquant. Installez backend/requirements.txt."
            ) from exc

        self._types = types
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._cache = EmbeddingCache(settings.embedding_cache_path)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed_texts([text], task_type="RETRIEVAL_QUERY")[0]

    def generate_json(self, prompt: str) -> dict[str, Any]:
        models = [settings.gemini_generation_model]
        if settings.gemini_fallback_model not in models:
            models.append(settings.gemini_fallback_model)

        last_error: Exception | None = None
        for model in models:
            try:
                response = _with_quota_retry(
                    lambda: self._client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=self._types.GenerateContentConfig(
                            temperature=0.2,
                            response_mime_type="application/json",
                        ),
                    ),
                    max_attempts=self._max_retry_attempts,
                )
                return _loads_json(response.text or "")
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Echec generation Gemini: {last_error}") from last_error

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        normalized = [_safe_text(text) for text in texts]
        cache_keys = [
            self._cache.key(settings.gemini_embedding_model, task_type, text)
            for text in normalized
        ]
        vectors: list[list[float] | None] = [
            self._cache.get(key) for key in cache_keys
        ]
        missing_indices = [
            index for index, vector in enumerate(vectors) if vector is None
        ]

        for batch_indices in _batched(missing_indices, size=64):
            batch_texts = [normalized[index] for index in batch_indices]
            batch_vectors = self._embed_batch(batch_texts, task_type)
            for index, vector in zip(batch_indices, batch_vectors):
                vectors[index] = vector
                self._cache.set(cache_keys[index], vector)
        self._cache.flush()

        if any(vector is None for vector in vectors):
            raise RuntimeError("Echec embeddings Gemini: vecteur manquant apres generation.")
        return vectors

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        models = [settings.gemini_embedding_model]
        if settings.gemini_embedding_fallback_model not in models:
            models.append(settings.gemini_embedding_fallback_model)

        last_error: Exception | None = None
        for model in models:
            try:
                response = _with_quota_retry(
                    lambda: self._client.models.embed_content(
                        model=model,
                        contents=texts,
                        config=self._types.EmbedContentConfig(task_type=task_type),
                    ),
                    max_attempts=self._max_retry_attempts,
                )
                embeddings = getattr(response, "embeddings", None)
                if embeddings:
                    return [list(item.values) for item in embeddings]
                embedding = getattr(response, "embedding", None)
                if embedding:
                    return [list(embedding.values)]
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Echec embeddings Gemini: {last_error}") from last_error


class EmbeddingCache:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._values: dict[str, list[float]] = {}
        self._dirty = False
        self._load()

    def key(self, model: str, task_type: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{model}:{task_type}:{digest}"

    def get(self, key: str) -> list[float] | None:
        return self._values.get(key)

    def set(self, key: str, vector: list[float]) -> None:
        self._values[key] = vector
        self._dirty = True

    def flush(self) -> None:
        if not self._dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._values), encoding="utf-8")
        self._dirty = False

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(raw, dict):
            self._values = {
                str(key): [float(item) for item in value]
                for key, value in raw.items()
                if isinstance(value, list)
            }


def _with_quota_retry(call, max_attempts: int):
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return call()
        except Exception as exc:
            last_error = exc
            if _is_retryable_quota_error(exc) and attempt == max_attempts:
                raise RuntimeError(
                    "Quota Gemini depasse apres plusieurs tentatives. "
                    "Attendez le reset du quota ou relancez avec moins de CV."
                ) from exc
            if not _is_retryable_quota_error(exc):
                raise
            time.sleep(_retry_delay_seconds(exc, attempt))
    raise RuntimeError(str(last_error)) from last_error


def _is_retryable_quota_error(exc: Exception) -> bool:
    message = str(exc)
    return "429" in message and (
        "RESOURCE_EXHAUSTED" in message or "Quota exceeded" in message
    )


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    message = str(exc)
    match = re.search(r"retryDelay': '(\d+)s'", message)
    if match:
        return min(float(match.group(1)) + 1.0, 30.0)
    match = re.search(r"Please retry in ([0-9.]+)s", message)
    if match:
        return min(float(match.group(1)) + 1.0, 30.0)
    return min(2.0 * attempt, 10.0)


class TestGeminiClient:
    """Deterministic Gemini stand-in used only when RAG_TEST_MODE=1."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_hash_embedding(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return _hash_embedding(text)

    def generate_json(self, prompt: str) -> dict[str, Any]:
        raise RuntimeError("TestGeminiClient ne genere pas de reponse LLM.")


def get_gemini_client() -> GeminiClient | TestGeminiClient:
    if settings.rag_test_mode:
        return TestGeminiClient()
    return GeminiClient()


def _loads_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def _batched(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _safe_text(text: str) -> str:
    text = " ".join(text.split())
    return text[:7000] if len(text) > 7000 else text


def _hash_embedding(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
