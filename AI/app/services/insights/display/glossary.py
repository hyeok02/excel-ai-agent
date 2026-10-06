"""Show a Korean reading of a source header without discarding the original."""
import re

from app.services.insights.display.glossary_terms import TERMS

HANGUL = re.compile(r"[가-힣]")
CJK_ONLY = re.compile(r"^[\u3400-\u9fff\u3040-\u30ff々〆〇]+$")
TRIM = re.compile(r"^[\s'\"(\[\-\u2013\u2014\u2022\u00b7]+|[\s'\".,:;)\]]+$")
# 원본 표에서 하위 항목은 "- Cash & Short Term Investments"처럼 들여쓰기 기호를 달고 온다.
# 표시할 때는 앞쪽 기호만 떼어낸다. 뒤쪽까지 떼면 "1 Year Growth (%)"의 괄호가 깨진다.
INDENT = re.compile(r"^[\s\u2013\u2014\u2022\u00b7-]+")
MAX_LENGTH = 60


def readable(value) -> str:
    """Render '한국어(원문)' when the term is known, else the original text."""
    text = INDENT.sub("", _display_text(value))
    korean = translate(text)
    return f"{korean}({text})" if korean else text


def translate(value) -> str:
    """The Korean reading of a source term, or an empty string when unknown."""
    text = TRIM.sub("", _display_text(value))
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


def _display_text(value) -> str:
    lines = [" ".join(line.split()) for line in str(value or "").splitlines()]
    lines = [line for line in lines if line]
    korean = [line for line in lines if HANGUL.search(line)]
    foreign = [line for line in lines if not HANGUL.search(line)]
    if len(korean) == len(foreign) == 1:
        translated = TERMS.get(foreign[0].casefold(), "")
        if CJK_ONLY.fullmatch(foreign[0]) or translated == korean[0]:
            return korean[0]
    return " ".join(lines)
