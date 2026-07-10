from collections import Counter, defaultdict
from math import log, sqrt

from ..models import Evidence
from .tokenizer import tokenize


class TfidfVectorStore:
    """Small deterministic vector store used for local RAG retrieval.

    It keeps the project runnable without external model downloads while still
    providing vectorized semantic-ish retrieval over CV chunks.
    """

    def __init__(self) -> None:
        self._documents: dict[str, list[tuple[str, str]]] = {}
        self._idf: dict[str, float] = {}
        self._vectors: dict[str, list[tuple[str, dict[str, float]]]] = {}

    def index(self, resume_id: str, chunks: list[str]) -> None:
        self._documents[resume_id] = [
            (f"{resume_id}_chunk_{index + 1}", chunk)
            for index, chunk in enumerate(chunks)
        ]
        self._rebuild()

    def search(self, resume_id: str, query: str, top_k: int = 5) -> list[Evidence]:
        if resume_id not in self._vectors:
            return []
        query_vector = self._vectorize(query)
        scored: list[Evidence] = []
        chunks_by_id = dict(self._documents.get(resume_id, []))
        for chunk_id, vector in self._vectors[resume_id]:
            similarity = _cosine(query_vector, vector)
            scored.append(
                Evidence(
                    source=chunk_id,
                    text=chunks_by_id.get(chunk_id, ""),
                    similarity=round(similarity, 4),
                )
            )
        scored.sort(key=lambda item: item.similarity, reverse=True)
        return scored[:top_k]

    def _rebuild(self) -> None:
        docs = [chunk for chunks in self._documents.values() for _, chunk in chunks]
        doc_count = max(len(docs), 1)
        document_frequency: defaultdict[str, int] = defaultdict(int)
        for chunk in docs:
            for token in set(tokenize(chunk)):
                document_frequency[token] += 1
        self._idf = {
            token: log((1 + doc_count) / (1 + frequency)) + 1
            for token, frequency in document_frequency.items()
        }
        self._vectors = {
            resume_id: [
                (chunk_id, self._vectorize(chunk))
                for chunk_id, chunk in chunks
            ]
            for resume_id, chunks in self._documents.items()
        }

    def _vectorize(self, text: str) -> dict[str, float]:
        tokens = tokenize(text)
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = sum(counts.values())
        return {
            token: (count / total) * self._idf.get(token, 1.0)
            for token, count in counts.items()
        }


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    common = set(left).intersection(right)
    dot = sum(left[token] * right[token] for token in common)
    left_norm = sqrt(sum(value * value for value in left.values()))
    right_norm = sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)

