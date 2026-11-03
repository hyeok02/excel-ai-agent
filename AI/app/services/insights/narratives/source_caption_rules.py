"""Recognize source-authored captions and populated cells without guessing subjects."""
import re


_META = re.compile(r"^(title|summary|제목|개요)\s*[:：]?$", re.I)
_EXCLUDE = re.compile(
    r"freeze panes|worksheet contains|please |click |select |refresh|"
    r"^\s*(?:source|data|note|footnote|http|copyright|자료출처|출처|주석)\s*[:：]|"
    r"\b(?:not|never|ignore|instruction)\b|아님|아닙|무시|명령", re.I,
)
_SECTION = re.compile(r"^(?:annual totals?|year to date|year\s*\d{4}|\d{4}|연간 합계|누적)$", re.I)


def _joined_captions(candidates):
    result = []
    for row, col, text, cited in candidates:
        if (result and row == result[-1][0] + len(result[-1][3])
                and col == result[-1][1]
                and re.match(r"^(?:by|for|in|during)\b", text, re.I)):
            previous = result[-1]
            result[-1] = (previous[0], col, previous[2] + " " + text, previous[3] + cited)
        else:
            result.append((row, col, text, cited))
    return result


def _caption(value, explicit=False):
    if not isinstance(value, str):
        return False
    text = " ".join(value.split()).strip()
    if not 15 <= len(text) <= (600 if explicit else 240) or _EXCLUDE.search(text) or _SECTION.fullmatch(text):
        return False
    if (re.search(r"\b(?:preliminary|provisional|final|revised)\b|잠정치|확정치|수정치", text, re.I)
            and re.match(r"^(?:(?:values?|figures?|data|estimates?)\s+(?:for\s+)?(?:19|20)\d{2}"
                         r"|(?:19|20)\d{2}(?:년|\s+(?:values?|figures?|data|estimates?)))", text, re.I)):
        return False  # a year-status sentence is not a new table boundary
    if text.startswith("(") and text.endswith(")"):
        return False  # a unit note alone is not a subject
    # Descriptive table-title syntax; a naked category ('New England') or
    # metric row ('Total Revenue') is insufficient to label an entire table.
    return bool(re.search(
        r"\b(?:table\s+[\w.]+|indicator\s+[\w.]+|percentage of|number of|"
        r"estimates?\s*:|by\s+|for\s+|timeseries|time series|average price|net generation)\b|"
        r"(?:현황|추이|통계|내역|분석|자료|보고서)", text, re.I,
    ))


def _cells(sheet):
    result = {}
    facts = sheet.get("business_facts", {})
    regions = facts.get("table_regions") or [{"rows": facts.get("table_rows", [])}]
    for region in regions:
        for row in region.get("rows", []):
            for cell in row:
                address = cell.get("cell")
                if address and cell.get("value") not in (None, ""):
                    result[address] = cell
    return result
