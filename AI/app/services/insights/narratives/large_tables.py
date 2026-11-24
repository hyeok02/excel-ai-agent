"""A table too large for the analysis sample (25,630행 × 28열), read once more from the file, column by column.

The sample stops at its cell cap, so its figures would describe the first rows only. The whole sheet is
streamed instead, keeping per-column totals only: the amount column ('Revenue', '매출') summed by a column
of few kinds ('Product_Category': 3) and, when one names the years ('FY20' · 'FY21'), by year.
"""
import re
from contextlib import contextmanager
from contextvars import ContextVar
from io import BytesIO

from app.services.insights.narratives.layout_tables import amount
from app.services.insights.narratives.narrative_values import insight, number, reference, topic_particle

_SOURCE: ContextVar[dict | None] = ContextVar("insight_source", default=None)
_MONEY = re.compile(r"revenue|sales|amount|cost|spend|profit|매출|금액|비용|수익|이익|판매액", re.I)
_PERIOD = re.compile(r"^(?:FY\s*'?\d{2,4}|(?:19|20)\d{2}\s*년?)$", re.I)
_ID = re.compile(r"\bid\b|_id$|번호|코드|code|alias|name|이름|명$", re.I)
MAX_CELLS = 2_000_000  # beyond this the file is told by its outline only
KINDS = 8  # a column of more kinds than this names things, it does not group them


@contextmanager
def reading(content):
    """The uploaded file's bytes, for a large table's second read while insights are built."""
    token = _SOURCE.set({"content": content, "read": {}})  # each sheet streamed once per request
    try:
        yield
    finally:
        _SOURCE.reset(token)


def large_table_facts(sheet, columns, top):
    """[(fact, cited)] read from the whole sheet: ``columns`` [(letter, header)], ``top`` the header row."""
    source = _SOURCE.get()
    if source is None or (sheet.get("rows") or 0) * (sheet.get("columns") or 0) > MAX_CELLS:
        return []
    key = (str(sheet.get("name")), tuple(columns), top)
    if key not in source["read"]:
        source["read"][key] = _facts(source["content"], sheet, columns, top)
    return source["read"][key]


def _facts(content, sheet, columns, top):
    from openpyxl import load_workbook
    from openpyxl.utils import column_index_from_string
    book = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        positions = {column_index_from_string(letter) - 1: (letter, header) for letter, header in columns}
        values = {letter: [] for letter, _ in columns}
        for row in book[str(sheet.get("name"))].iter_rows(min_row=top + 1, values_only=True):
            for position, (letter, _) in positions.items():
                values[letter].append(row[position] if position < len(row) else None)
    finally:
        book.close()
    numeric = lambda letter: [v for v in values[letter] if isinstance(v, (int, float)) and not isinstance(v, bool)]  # noqa
    measure = next(((letter, header) for letter, header in columns if _MONEY.search(header)
                    and len(numeric(letter)) >= 0.9 * len(values[letter])), None)
    if measure is None:
        return []
    groups = [(letter, header) for letter, header in columns if not _ID.search(header) and letter != measure[0]
              and all(isinstance(v, str) for v in values[letter] if v is not None)
              and 2 <= len(set(values[letter]) - {None}) <= KINDS]
    facts, rows = [], sum(v is not None for v in values[measure[0]])
    for letter, header in sorted(groups, key=lambda group: not all(_PERIOD.match(str(v).strip())
                                                                     for v in values[group[0]] if v is not None))[:2]:
        totals = {}
        for key, value in zip(values[letter], values[measure[0]]):
            if key is not None and isinstance(value, (int, float)):
                totals[str(key).strip()] = totals.get(str(key).strip(), 0) + value
        periods = all(_PERIOD.match(key) for key in totals)
        ordered = sorted(totals.items()) if periods else sorted(totals.items(), key=lambda item: -item[1])
        listed = ", ".join(f"{key} {amount(value)}" for key, value in ordered)
        fact = f"{header}별 {measure[1]} 합계는 {listed}입니다(전체 {number(rows)}건)."
        kept = [item for item in ordered if item[1]]  # FY22 with nothing entered yet is no year to compare with
        if periods and len(kept) >= 2 and kept[0][1] != kept[-1][1]:
            (first, old), (last, new) = kept[0], kept[-1]
            rate = (new - old) / abs(old) * 100
            fact += f" {first} 대비 {last}{topic_particle(last)} {abs(rate):.1f}% {'증가' if rate > 0 else '감소'}했습니다."
        facts.append((fact, [reference(sheet["name"], f"{letter}{top}"), reference(sheet["name"], f"{measure[0]}{top}")]))
    return facts


def large_table_insights(sheet, columns, top):
    return [insight(f"{fact.split('별 ', 1)[0]}별 합계", fact, cited, "metric") for fact, cited in
            large_table_facts(sheet, columns, top)]


def whole_sheet_note(limitations, insights):
    """'아래 수치는 읽은 범위에서만 집계' is not said of totals read from the whole sheet ('전체 25,630건')."""
    if not any(re.search(r"\(전체 [\d,]+건\)", item.fact) for item in insights):
        return limitations
    return [note.replace("아래 수치는 읽은 범위에서만 집계한 값입니다.", "‘전체 N건’으로 밝힌 합계는 파일 전체에서 다시 계산했고, "
                         "나머지 수치는 읽은 범위에서만 집계한 값입니다.") for note in limitations]
