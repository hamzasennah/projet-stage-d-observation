from app.services.chunker import split_text


def test_split_text_handles_overlap_without_looping() -> None:
    text = " ".join(f"mot{i}" for i in range(400))
    chunks = split_text(text, chunk_size=120, overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)
    assert chunks[0] != chunks[1]


def test_split_text_empty_input() -> None:
    assert split_text("   ") == []

