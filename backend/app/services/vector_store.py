from __future__ import annotations

import re

from ..config import settings
from ..models import Evidence, ResumeRecord


class ChromaResumeStore:
    def __init__(self, collection_name: str | None = None) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "ChromaDB est manquant. Installez backend/requirements.txt."
            ) from exc

        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.chroma_path))
        if collection_name is None:
            suffix = "test" if settings.rag_test_mode else settings.gemini_embedding_model
            collection_name = f"resume_chunks_{_safe_collection_suffix(suffix)}"
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset_analysis(self, analysis_id: str) -> None:
        try:
            self._collection.delete(where={"analysis_id": analysis_id})
        except Exception:
            pass

    def index_resume(
        self,
        analysis_id: str,
        resume: ResumeRecord,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        if not chunks:
            return
        ids: list[str] = []
        metadatas: list[dict[str, str | int]] = []
        for index, _ in enumerate(chunks, start=1):
            ids.append(f"{analysis_id}:{resume.id}:{index}")
            metadatas.append(
                {
                    "analysis_id": analysis_id,
                    "resume_id": resume.id,
                    "analysis_resume_id": f"{analysis_id}:{resume.id}",
                    "candidate_name": resume.candidate_name,
                    "resume_title": resume.title,
                    "source_file": resume.source_file,
                    "chunk_index": index,
                }
            )
        self._collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search_resume(
        self,
        analysis_id: str,
        resume_id: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[Evidence]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"analysis_resume_id": f"{analysis_id}:{resume_id}"},
            include=["documents", "metadatas", "distances"],
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        evidence: list[Evidence] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            chunk_index = metadata.get("chunk_index", "?") if metadata else "?"
            title = metadata.get("resume_title", resume_id) if metadata else resume_id
            similarity = max(0.0, 1.0 - float(distance))
            evidence.append(
                Evidence(
                    source=f"{title} - chunk {chunk_index}",
                    text=document,
                    similarity=round(similarity, 4),
                )
            )
        return evidence


def _safe_collection_suffix(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")[:40] or "default"
