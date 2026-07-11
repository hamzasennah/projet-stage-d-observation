from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from ..config import settings
from .tokenizer import tokenize


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiClient:
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
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=self._types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                )
                return _loads_json(response.text or "")
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Echec generation Gemini: {last_error}") from last_error

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in _batched([_safe_text(text) for text in texts], size=64):
            vectors.extend(self._embed_batch(batch, task_type))
        return vectors

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        models = [settings.gemini_embedding_model]
        if settings.gemini_embedding_fallback_model not in models:
            models.append(settings.gemini_embedding_fallback_model)

        last_error: Exception | None = None
        for model in models:
            try:
                response = self._client.models.embed_content(
                    model=model,
                    contents=texts,
                    config=self._types.EmbedContentConfig(task_type=task_type),
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

