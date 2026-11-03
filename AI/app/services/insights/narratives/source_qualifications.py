"""Year-specific data status from source notes, never from generated prose."""
import re

from openpyxl.utils.cell import coordinate_to_tuple

from app.services.insights.narratives.narrative_values import reference
from app.services.insights.narratives.source_context import source_table_window
from app.services.insights.verification.validation_index import extract_references

_YEAR = r"(?:19|20)\d{2}"
_YEARS = rf"{_YEAR}(?:\s*(?:,\s*(?:and\s+)?|and\s+|&\s*){_YEAR})*"
_STATUS = re.compile(r"\b(?:preliminary|provisional|final|revised)\b|잠정|확정|수정치", re.I)
_ENGLISH = re.compile(
    rf"(?:values?|figures?|data|estimates?)\s+(?:for\s+)?"
    rf"(?P<years>{_YEARS})(?:\s+and\s+prior\s+years)?\s+"
    r"(?:are|is)\s+(?P<status>.+)", re.I,
)
_YEAR_FIRST = re.compile(
    rf"(?P<years>{_YEARS})\s+(?:values?|figures?|data|estimates?)\s+"
    r"(?:are|is)\s+(?P<status>.+)", re.I,
)
_KOREAN = re.compile(
    rf"(?P<years>{_YEAR}년(?:\s*(?:,|및|과|와)\s*{_YEAR}년)*)\s*"
    r"(?:수치|자료|데이터|추정치|값)(?:는|은|가|이)?\s*(?P<status>.+)",
)
_PREFIX = re.compile(r"^\s*(?:(?:notes?|주석|참고)\s*[:：]\s*)?[-•]?\s*", re.I)
_KNOWN = [
    (re.compile(r"(?:preliminary|provisional)(?:\s+(?:values?|figures?|data|estimates?))?"
                r"(?:\s+based\s+on\s+.+)?", re.I), "잠정치"),
    (re.compile(r"final(?:\s+(?:values?|figures?|data|estimates?))?", re.I), "확정치"),
    (re.compile(r"revised(?:\s+(?:values?|figures?|data|estimates?))?", re.I), "수정치"),
    (re.compile(r"잠정(?:치|값|자료)?(?:입니다|이다|임)?"), "잠정치"),
    (re.compile(r"확정(?:치|값|자료)?(?:입니다|이다|임)?"), "확정치"),
    (re.compile(r"수정치(?:입니다|이다|임)?"), "수정치"),
]


def source_qualifications(context, item):
    """Return (qualification sentence, source references) for this fact's years.

    Only a single cited sheet can lend a sheet-wide status note. Year lists are
    explicit, and the years must be dates in the selected canonical fact. A
    numeric amount that happens to look like a year supplies no date context.
    """
    years = set(re.findall(rf"(?<![\w,.])({_YEAR})\s*년", item.fact))
    years.update(re.findall(rf"(?<![\w,.])({_YEAR})[-/]\d{{1,2}}[-/]\d{{1,2}}\b", item.fact))
    if not years:
        return "", []
    names = {ref.partition("!")[0] for value in item.evidence
             for ref in extract_references(str(value))}
    if len(names) != 1:
        return "", []
    name = next(iter(names))
    sheet = next((s for s in context.get("sheets", [])
                  if isinstance(s, dict) and str(s.get("name", "")).casefold() == name), None)
    if not sheet:
        return "", []
    window = source_table_window(context, item)
    if window is None:
        return "", []
    _, first_row, next_row, first_col, next_col = window
    found = {}
    for cell in _note_cells(sheet):
        try:
            row, col = coordinate_to_tuple(cell["cell"])
        except (KeyError, ValueError):
            continue
        if not (first_row <= row < next_row and first_col <= col < next_col):
            continue
        value = cell.get("value")
        if not isinstance(value, str) or not _STATUS.search(value):
            continue
        for clause in re.split(r"(?<=[.!?。;])\s+|[\r\n]+", value):
            clause = _PREFIX.sub("", clause).strip().rstrip(".;。")
            match = next((m for pattern in (_ENGLISH, _YEAR_FIRST, _KOREAN)
                          if (m := pattern.fullmatch(clause))), None)
            if not match:
                continue
            relevant = set(re.findall(_YEAR, match["years"])) & years
            status = match["status"].strip()
            if not relevant or not _STATUS.search(status):
                continue
            # Keep unsupported qualifiers verbatim. In particular, 'not final',
            # 'partly preliminary', or alternatives never become definite status.
            label = next((label for pattern, label in _KNOWN if pattern.fullmatch(status)), "")
            if not label and len(clause) > 240:
                continue
            ref = reference(sheet["name"], cell["cell"])
            for year in relevant:
                found.setdefault(year, []).append((label, clause, ref))
    parts, refs = [], []
    for year, entries in sorted(found.items()):
        labels = {entry[0] for entry in entries}
        if len(labels) == 1 and "" not in labels:
            parts.append(f"{year}년 수치는 원본에서 {next(iter(labels))}로 표시되어 있습니다.")
            refs.extend(entry[2] for entry in entries)
        else:
            # Conflicting source notes are reported as source wording, not
            # resolved by arbitrary row order or by making every year preliminary.
            quotes = list(dict.fromkeys(entry[1] for entry in entries))[:2]
            parts.append("원본 주석: " + " / ".join(f"‘{quote}’" for quote in quotes) + ".")
            refs.extend(entry[2] for entry in entries if entry[1] in quotes)
    return " ".join(dict.fromkeys(parts)), list(dict.fromkeys(refs))


def _note_cells(sheet):
    seen = set()
    facts = sheet.get("business_facts", {})
    regions = facts.get("table_regions") or [{"rows": facts.get("table_rows", [])}]
    cells = list(sheet.get("source_notes", []))
    for region in [*regions, *sheet.get("region_samples", [])]:
        cells.extend(cell for row in region.get("rows", region.get("analysis_rows", [])) for cell in row)
    for original in cells:
        cell = dict(original)
        address = cell.get("cell") or cell.get("address")
        if address and cell.get("value") not in (None, "") and address not in seen:
            seen.add(address)
            cell["cell"] = address
            yield cell
