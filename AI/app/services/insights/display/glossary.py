"""Show a Korean reading of a source header without discarding the original."""
import re

from app.services.insights.display.glossary_terms import TERMS

HANGUL = re.compile(r"[가-힣]")
TRIM = re.compile(r"^[\s'\"(\[]+|[\s'\".,:;)\]]+$")
MAX_LENGTH = 60


def readable(value) -> str:
    """Render '한국어(원문)' when the term is known, else the original text."""
    text = " ".join(str(value or "").split())
    korean = translate(text)
    return f"{korean}({text})" if korean else text


def translate(value) -> str:
    """The Korean reading of a source term, or an empty string when unknown."""
    text = TRIM.sub("", " ".join(str(value or "").split()))
    if not text or len(text) > MAX_LENGTH or HANGUL.search(text):
        return ""
    direct = TERMS.get(text.casefold())
    if direct:
        return direct
    return _path(text)


def _path(text):
    """Header paths such as 'Department > General & Administrative'."""
    parts = [part.strip() for part in text.split(">")]
    if len(parts) < 2:
        return ""
    found = [TERMS.get(part.casefold(), "") for part in parts]
    if not all(found):
        return ""
    return " > ".join(found)
