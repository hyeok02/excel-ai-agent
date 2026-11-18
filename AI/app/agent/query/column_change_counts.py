"""Count the rows whose newer value is above (or below) their older one, as a last resort.

"상업용 전기요금이 작년보다 오른 주는 몇 개야?" compares, in every row, two columns of one parent
header (Commercial: August 2026 and August 2025). No plan can state "D > E", so this runs only
when every other stage has answered nothing. The parent is read among the table's own parent
headers; the rows counted are those the question names (주 → states, not census divisions or the
U.S. total), read like a member ranking. Each counted row is cited, and every reading is stated.
"""
import asyncio
import re

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.series_topic_names import series_words
from app.agent.query.tabular_catalog import build_query_tables
from app.services.insights.facts.fact_trends import date_value

_COUNT = re.compile(r"몇\s*(?:개|곳|군데|건|명|주|개국)|개수|(?:수|숫자)(?:는|가)\s*(?:몇|얼마)")
_UP = re.compile(r"올랐|오른|상승|증가|늘어|늘었|높아|많아|커진|커졌")
_DOWN = re.compile(r"내렸|내린|하락|감소|줄어|줄었|낮아|적어|작아")
_THAN = re.compile(r"보다|대비|전년|작년|지난\s*해|이전")
MAX_LISTED, MAX_EVIDENCE = 15, 60


def column_change_count_answer(question, summary, index, resolver=None, classifier=None):
    up, down = bool(_UP.search(question)), bool(_DOWN.search(question))
    if summary is None or index is None or up == down or not _COUNT.search(question) or not _THAN.search(question):
        return None
    pairs = [pair for table in build_query_tables(summary) if table.complete for pair in _pairs(table)]
    if not pairs:
        return None
    try:
        return asyncio.run(_answer(question, index, pairs, up, resolver, classifier))
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None


async def _answer(question, index, pairs, up, resolver, classifier):
    if len(pairs) > 1:
        if resolver is None:
            from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
            resolver = LangChainSourceLabelResolver.from_environment()
        parents = list(dict.fromkeys(parent for _, parent, _, _ in pairs))
        readings = await asyncio.gather(*(resolver.resolve(word, "column group", parents) for word in series_words(question)))
        named = {parents[item.candidate_id] for item in readings if item.status == "resolved"
                 and type(item.candidate_id) is int and 0 <= item.candidate_id < len(parents)}
        pairs = [pair for pair in pairs if pair[1] in named]
        if len(pairs) != 1:
            return None  # no group, or several, named: the comparison is not one reading
    table, parent, older, newer = pairs[0]
    label = next((column for column in table.columns if all(
        isinstance(row.values.get(column.id), str) for row in table.rows if row.values.get(column.id) not in (None, ""))), None)
    rows = [row for row in table.rows if label is not None and isinstance(row.values.get(label.id), str)
            and all(_number(row.values.get(column.id)) for column in (older, newer))]
    names = [" ".join(row.values[label.id].split()) for row in rows]
    if len(rows) < 2 or len(set(names)) != len(names):
        return None
    if classifier is None:
        from app.agent.query.row_kind_classifier import LangChainRowKindClassifier
        classifier = LangChainRowKindClassifier.from_environment()
    if classifier is None:
        return None
    reading = await classifier.classify(question, " ".join(label.header.split()), names)
    chosen = sorted({number for number in reading.candidate_ids if 0 <= number < len(rows)})
    if reading.status != "selected" or not chosen:
        return None
    counted = [number for number in chosen if (rows[number].values[newer.id] > rows[number].values[older.id]) == up
               and rows[number].values[newer.id] != rows[number].values[older.id]]
    kind = reading.kind.strip() or "행"
    excluded = [names[number] for number in range(len(rows)) if number not in set(chosen)]
    listed = ", ".join(names[number] for number in counted[:MAX_LISTED]) + (
        f" 외 {len(counted) - MAX_LISTED}개" if len(counted) > MAX_LISTED else "")
    text = (f"{parent} 기준 {_header(newer)} 값이 {_header(older)}보다 {'높은' if up else '낮은'} {kind}: "
            f"{len(counted)}개 (비교한 {len(chosen)}개 중)" + (f"\n{listed}" if counted else ""))
    source = {cell.reference: cell for row in index.rows if row.sheet_name == table.sheet_name for cell in row.cells}
    references = [label.header_reference, older.header_reference, newer.header_reference,
                  *(reference for reference, _ in newer.header_path),
                  *(f"{table.sheet_name}!{_letter(column)}{rows[number].row_number}"
                    for number in counted for column in (label, older, newer))]
    notes = [f"‘{parent}’의 {_header(newer)}·{_header(older)} 열을 같은 행끼리 비교해 원본 전체 행에서 셌습니다."]
    if excluded:
        notes.append(f"‘{kind}’에 해당하지 않는다고 이름으로 판단해 제외한 행: {', '.join(excluded[:MAX_LISTED])}"
                     + (f" 외 {len(excluded) - MAX_LISTED}개" if len(excluded) > MAX_LISTED else ""))
    return QuestionAnswer(
        question=question, answer=text, status=QuestionAnswerStatus.LIMITED, confidence=0.8,
        selected_tools=["column_change_count"],
        evidence=[_evidence(source[key]) for key in dict.fromkeys(references) if key in source][:MAX_EVIDENCE],
        limitations=notes, verification=QuestionAnswerVerification(
            level="source_checked", checks=["source_values", "calculation", "semantic_alias_resolved"]))


def _pairs(table):
    """(table, parent, older, newer) for each parent header over exactly two dated numeric columns."""
    groups = {}
    for column in table.columns:
        parent = " · ".join(text for _, text in column.header_path)
        if parent and _when(column) is not None:
            groups.setdefault(parent, []).append(column)
    for parent, columns in groups.items():
        if len(columns) == 2 and type(_when(columns[0])) is type(_when(columns[1])) and _when(columns[0]) != _when(columns[1]):
            older, newer = sorted(columns, key=_when)
            yield table, parent, older, newer


def _when(column):
    header = _header(column)
    return date_value(header) or (int(header) if re.fullmatch(r"(?:19|20|21)\d{2}", header) else None)


def _header(column):
    return " ".join(column.header.split())


def _letter(column):
    return "".join(character for character in column.header_reference.rsplit("!", 1)[-1] if character.isalpha())


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
