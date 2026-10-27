"""Protect exact indexed data from being interpreted as question separators."""
import re

_QUALIFIER = re.compile(
    r"(?:단위|통화|소수점(?:\s*\d+\s*자리)?|출처|근거)(?:도|는|까지|를|을)?\s*"
    r"(?:함께\s*)?(?:알려\s*줘|알려주세요|보여\s*줘|표시해\s*줘|표시해주세요|포함해\s*줘)[.!?。？！]*"
)
_CHANGE = re.compile(r"증가|감소|변화|증감|\bchange\b|\bgrowth\b", re.I)
_CHANGE_FORMAT = re.compile(r"금액\s*과\s*(?:증가율|감소율|증감률|변화율)을?\s*알려\s*줘[.!?。？！]*")
_DELIMITING_LITERAL = re.compile(r"[;；\n?？:：]|"
    r"(?:비교하|계산하|요약하|조회하|분석하|정리하|확인하|보여주|알려주|구하|찾아주)고(?:\s|,|$)")
_SOURCE_SCOPE_SUFFIX = re.compile(
    r"\(\s*[^()\r\n?？;；]{1,200}?\s+(?:시트|범위)\s*(?:기준|내에서|에서)\s*\)"
    r"|\(\s*(?:in|on|using)\s+(?:sheet|range)\s+[^()\r\n?？;；]{1,200}\)", re.I
)


def source_qualifier_end(question, start, sources):
    """Recognize a scope annotation, never discard its original source text.

    Resolver wording may omit words like 'sheet' and 'based on'. An exact
    current source sheet name still identifies scope, not another question.
    Unknown parenthesized text keeps the normal compound-question behavior.
    """
    if explicit := _SOURCE_SCOPE_SUFFIX.match(question, start):
        return explicit.end()
    if start >= len(question) or question[start] != "(":
        return None
    summary = getattr(sources, "summary", None)
    names = {sheet.name for sheet in getattr(summary, "sheets", ())}
    if not names:
        index = getattr(sources, "original_index", None) or getattr(sources, "index", None)
        names = {row.sheet_name for row in getattr(index, "rows", ())}
    for name in sorted(names, key=len, reverse=True):
        text = re.escape(name)
        literal = rf"(?:{text}|'{text}'|\"{text}\"|‘{text}’|“{text}”)"
        if match := re.compile(rf"\(\s*{literal}\s*\)", re.I).match(question, start):
            return match.end()
    return None


def mask_source_literals(question, mask, sources):
    """A bounded lexical aid only: never read providers or prove population scope."""
    index = getattr(sources, "original_index", None) or getattr(sources, "index", None)
    chars, visited, seen = list(mask), 0, set()
    for row in getattr(index, "rows", ()):
        for cell in row.cells:
            visited += 1
            if visited > 50_000:
                return "".join(chars)
            value = cell.value
            if not isinstance(value, str) or not 2 <= len(value) <= len(question) or value in seen:
                continue
            seen.add(value)
            if not _DELIMITING_LITERAL.search(value):
                continue
            start = question.find(value)
            while start >= 0:
                chars[start:start + len(value)] = " " * len(value)
                start = question.find(value, start + len(value))
    return "".join(chars)


def merge_format_continuations(question, spans):
    """Keep ancillary display requests in their original query, including punctuation."""
    merged = []
    for start, end in spans:
        current = question[start:end].strip()
        prior = question[merged[-1][0]:merged[-1][1]] if merged else ""
        if merged and (_QUALIFIER.fullmatch(current)
                       or (_CHANGE.search(prior) and _CHANGE_FORMAT.fullmatch(current))):
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged
