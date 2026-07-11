import re
import unicodedata


TOKEN_RE = re.compile(r"[a-z0-9+#]+")


def normalize_text(text: str) -> str:
    """Lowercase text and remove accents for robust matching."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = without_accents.lower()
    lowered = lowered.replace("/", " ").replace("-", " ")
    return re.sub(r"\s+", " ", lowered).strip()


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(normalize_text(text))


def keyword_in_text(keyword: str, text: str) -> bool:
    keyword_norm = normalize_text(keyword)
    text_norm = normalize_text(text)
    if not keyword_norm:
        return False
    compact_keyword = keyword_norm.replace(" ", "")
    compact_text = text_norm.replace(" ", "")
    if " " in keyword_norm:
        return keyword_norm in text_norm or compact_keyword in compact_text
    return keyword_norm in set(tokenize(text_norm))


def matched_keywords(keywords: list[str], text: str) -> list[str]:
    return [keyword for keyword in keywords if keyword_in_text(keyword, text)]
