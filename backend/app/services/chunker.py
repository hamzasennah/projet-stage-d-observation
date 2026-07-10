import re


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size doit etre positif")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap doit etre compris entre 0 et chunk_size - 1")

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    units = _split_into_units(normalized, chunk_size)
    chunks: list[str] = []
    current = ""

    for unit in units:
        candidate = f"{current} {unit}".strip()
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = _with_overlap(chunks[-1] if chunks else "", unit, overlap, chunk_size)

    if current:
        chunks.append(current)

    return chunks


def _split_into_units(text: str, chunk_size: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= chunk_size:
            units.append(paragraph)
            continue
        sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(paragraph) if s.strip()]
        for sentence in sentences:
            if len(sentence) <= chunk_size:
                units.append(sentence)
            else:
                units.extend(
                    sentence[i : i + chunk_size]
                    for i in range(0, len(sentence), chunk_size)
                )
    return units


def _with_overlap(previous: str, next_unit: str, overlap: int, chunk_size: int) -> str:
    if not previous or overlap == 0:
        return next_unit[:chunk_size]
    prefix = previous[-overlap:].strip()
    candidate = f"{prefix} {next_unit}".strip()
    return candidate[:chunk_size]

