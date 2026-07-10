from pathlib import Path
import re


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def extract_text(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Format non supporte: {suffix or 'sans extension'}")
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix == ".docx":
        return extract_docx_text(path)
    return clean_text(path.read_text(encoding="utf-8"))


def extract_pdf_text(path: Path) -> str:
    import fitz

    chunks: list[str] = []
    with fitz.open(path) as pdf:
        for page in pdf:
            chunks.append(page.get_text("text"))
    return clean_text("\n".join(chunks))


def extract_docx_text(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return clean_text("\n".join(paragraphs))


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

