"""Conservative exact-coverage splitting; source text is never paraphrased."""
import re
from dataclasses import dataclass
from app.agent.query.composite_source_text import mask_source_literals, merge_format_continuations

_ACTION = re.compile(r"(?:비교하|계산하|요약하|조회하|분석하|정리하|확인하|보여주|알려주|구하|찾아주)고(?=\s|,)")
_RANGE = re.compile(r"\$?[A-Z]{1,3}\$?[1-9]\d*:\$?[A-Z]{1,3}\$?[1-9]\d*", re.I)
_TIME = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_AUXILIARY = re.compile(r"\s*(?:있|싶|계시|나서|난\s*(?:후|다음)|보니|보면)")
_MARKER_SUFFIX = re.compile(r"(?:인|이면|이거나|이며|이고|이\s*아닌|가\s*아닌)(?:\s|$)")
_DEPENDENT = re.compile(r"(?:그\s*(?:중|결과|항목|대상|사람|값)|이\s*(?:결과|항목|대상)|해당|"
                        r"앞(?:의|서)|위(?:의|에서|\s+결과)|나머지|그것|그걸|거기|그곳|동일한|같은\s*(?:조건|시트)|"
                        r"among\s+(?:them|those)|of\s+those|the\s+rest|their|then\b|those\b)", re.I)


@dataclass(frozen=True)
class CompoundQuestion:
    shared_prefix: str
    parts: tuple[str, ...]
    error: str | None = None

    def question_for(self, position):
        return " ".join(item for item in (self.shared_prefix, self.parts[position]) if item)


def split_compound_question(question, sources=None):
    """Return None for a single request, including ordinary AND row filters."""
    mask = _outside_text(question)
    if not (re.search(r"[;；\n?？]", mask) or _ACTION.search(mask)):
        return None
    mask = mask_source_literals(question, mask, sources)
    separators = [(match.start(), match.end()) for match in re.finditer(r"[;；\n]+", mask)]
    for match in re.finditer(r"[?？]", mask):
        if match.end() < len(question) and not question[match.end()].isspace():
            continue
        end = match.end() + re.match(r"\s*", question[match.end():]).end()
        if question[end:].strip() and not _MARKER_SUFFIX.match(question[end:]):
            separators.append((match.end(), end))
    for match in _ACTION.finditer(mask):
        if _AUXILIARY.match(question[match.end():]):
            continue
        end = re.match(r"\s*,?\s*(?:그리고\s+)?", question[match.end():]).end() + match.end()
        if question[end:].strip():
            separators.append((match.end(), end))
    separators.sort()
    if not separators:
        return None
    spans, cursor = [], 0
    for start, end in separators:
        if start < cursor:
            continue
        if question[cursor:start].strip():
            spans.append((cursor, start))
        cursor = end
    if question[cursor:].strip():
        spans.append((cursor, len(question)))
    spans = merge_format_continuations(question, spans)
    if len(spans) < 2:
        return None
    prefix = ""
    first_start, first_end = spans[0]
    colon = [match.start() for match in re.finditer(r"[:：]", mask[first_start:first_end])]
    if len(colon) == 1:
        cut = first_start + colon[0]
        prefix = question[:cut].strip()
        spans[0] = (cut + 1, first_end)
    parts = tuple(question[start:end].strip() for start, end in spans)
    error = "한 번에 2~4개의 명확한 질문으로 나누어 주세요." if len(parts) > 4 or not all(parts) else None
    return CompoundQuestion(prefix, parts, error)


def dependent_part(text):
    return bool(_DEPENDENT.search(_outside_text(text.strip())))


def _outside_text(text):
    # Quotes, source addresses and parenthesized headers are data, not grammar.
    chars = list(text)
    stack, quote = [], None
    pairs = {"'": "'", '"': '"', "‘": "’", "“": "”", "`": "`"}
    brackets = {"(": ")", "[": "]", "{": "}"}
    for position, char in enumerate(text):
        if quote:
            chars[position] = " "
            if char == quote:
                quote = None
        elif char in pairs:
            if char == "'" and position and position + 1 < len(text) and text[position - 1].isalnum() and text[position + 1].isalnum():
                continue
            quote, chars[position] = pairs[char], " "
        elif char in brackets:
            stack.append(brackets[char])
            chars[position] = " "
        elif stack:
            chars[position] = " "
            if char == stack[-1]:
                stack.pop()
    for pattern in (_RANGE, _TIME):
        for match in pattern.finditer(text):
            chars[match.start():match.end()] = " " * (match.end() - match.start())
    return "".join(chars)
