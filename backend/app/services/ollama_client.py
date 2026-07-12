from __future__ import annotations

import hashlib
import json
import math
import re
import socket
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..config import settings
from .tokenizer import tokenize


class OllamaConfigurationError(RuntimeError):
    pass


class OllamaConnectionError(RuntimeError):
    pass


class OllamaModelError(RuntimeError):
    pass


class OllamaClient:
    _embedding_batch_size = 32
    _embedding_timeout_seconds = 180
    _generation_timeout_seconds = 240

    def __init__(self) -> None:
        if settings.llm_provider != "ollama":
            raise OllamaConfigurationError("LLM_PROVIDER doit etre defini a 'ollama'.")
        if not settings.ollama_base_url:
            raise OllamaConfigurationError("OLLAMA_BASE_URL est manquant.")
        if not settings.ollama_generation_model:
            raise OllamaConfigurationError("OLLAMA_GENERATION_MODEL est manquant.")
        if not settings.ollama_embedding_model:
            raise OllamaConfigurationError("OLLAMA_EMBEDDING_MODEL est manquant.")

        self._base_url = settings.ollama_base_url
        self._cache = EmbeddingCache(settings.embedding_cache_path)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts(texts, purpose="document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed_texts([text], purpose="query")[0]

    def generate_json(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": settings.ollama_generation_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_ctx": 8192,
            },
        }
        response = self._post_json(
            "/api/generate",
            payload,
            timeout=self._generation_timeout_seconds,
        )
        text = str(response.get("response") or "").strip()
        if not text:
            raise RuntimeError("Ollama a retourne une reponse vide.")
        return _loads_json(text)

    def _embed_texts(self, texts: list[str], purpose: str) -> list[list[float]]:
        normalized = [_safe_text(text) for text in texts]
        cache_keys = [
            self._cache.key(settings.ollama_embedding_model, purpose, text)
            for text in normalized
        ]
        vectors: list[list[float] | None] = [
            self._cache.get(key) for key in cache_keys
        ]
        missing_indices = [
            index for index, vector in enumerate(vectors) if vector is None
        ]

        for batch_indices in _batched(missing_indices, size=self._embedding_batch_size):
            batch_texts = [normalized[index] for index in batch_indices]
            batch_vectors = self._embed_batch(batch_texts)
            for index, vector in zip(batch_indices, batch_vectors):
                vectors[index] = vector
                self._cache.set(cache_keys[index], vector)
        self._cache.flush()

        if any(vector is None for vector in vectors):
            raise RuntimeError("Echec embeddings Ollama: vecteur manquant apres generation.")
        return [vector for vector in vectors if vector is not None]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {
            "model": settings.ollama_embedding_model,
            "input": texts,
            "truncate": True,
        }
        response = self._post_json(
            "/api/embed",
            payload,
            timeout=self._embedding_timeout_seconds,
        )
        embeddings = response.get("embeddings")
        if embeddings is None and isinstance(response.get("embedding"), list):
            embeddings = [response["embedding"]]
        if not isinstance(embeddings, list):
            raise RuntimeError("Echec embeddings Ollama: champ 'embeddings' absent.")
        vectors = [_as_float_vector(item) for item in embeddings]
        if len(vectors) != len(texts):
            raise RuntimeError(
                "Echec embeddings Ollama: nombre de vecteurs different du nombre de textes."
            )
        return vectors

    def _post_json(self, endpoint: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self._base_url}{endpoint}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise _ollama_http_error(exc.code, error_body) from exc
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise OllamaConnectionError(
                "Ollama n'est pas joignable. Lancez Ollama localement et verifiez "
                f"OLLAMA_BASE_URL={self._base_url}."
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama a retourne une reponse non JSON.") from exc
        if not isinstance(data, dict):
            raise RuntimeError("Ollama a retourne un format inattendu.")
        return data


class EmbeddingCache:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._values: dict[str, list[float]] = {}
        self._dirty = False
        self._load()

    def key(self, model: str, purpose: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{model}:{purpose}:{digest}"

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


class TestOllamaClient:
    """Client deterministe utilise uniquement quand RAG_TEST_MODE=1."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_hash_embedding(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return _hash_embedding(text)

    def generate_json(self, prompt: str) -> dict[str, Any]:
        raise RuntimeError("TestOllamaClient ne genere pas de reponse LLM.")


def get_ollama_client() -> OllamaClient | TestOllamaClient:
    if settings.rag_test_mode:
        return TestOllamaClient()
    return OllamaClient()


def _ollama_http_error(status_code: int, body: str) -> RuntimeError:
    detail = _extract_error_detail(body)
    if status_code == 404:
        return OllamaModelError(
            "Modele Ollama introuvable. Telechargez les modeles avec "
            "`ollama pull qwen3-embedding:0.6b` et `ollama pull qwen2.5:7b`."
        )
    if status_code in {400, 422}:
        return OllamaModelError(f"Requete Ollama refusee: {detail}")
    return RuntimeError(f"Erreur Ollama HTTP {status_code}: {detail}")


def _extract_error_detail(body: str) -> str:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body.strip() or "detail indisponible"
    if isinstance(parsed, dict):
        return str(parsed.get("error") or parsed.get("detail") or parsed)
    return str(parsed)


def _loads_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?", "", candidate).strip()
        candidate = re.sub(r"```$", "", candidate).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(candidate[start : end + 1])

    if not isinstance(parsed, dict):
        raise RuntimeError("Le LLM doit retourner un objet JSON.")
    return parsed


def _batched(items: list[int], size: int) -> list[list[int]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _safe_text(text: str) -> str:
    text = " ".join(text.split())
    return text[:7000] if len(text) > 7000 else text


def _as_float_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        raise RuntimeError("Echec embeddings Ollama: vecteur non valide.")
    vector = [float(item) for item in value]
    if not vector:
        raise RuntimeError("Echec embeddings Ollama: vecteur vide.")
    return vector


def _hash_embedding(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
