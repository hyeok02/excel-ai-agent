"""How much one named row's newer value moved from its older one, as a last resort.

"하와이 상업용 전기요금은 작년보다 얼마나 올랐어?" names one row (Hawaii) and one parent header over
two dated columns (Commercial: August 2025 and August 2026). The parent is read among the
table's parent headers and the row among the row names, exactly as a change count reads them;
the change is computed from the two cited cells and stated with its direction as it is in the
source, whatever direction the question assumed. Every reading is stated.
"""
import asyncio
import re

from app.agent.query.column_change_counts import _THAN, _header, _letter, _number, _pairs
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.series_topic_names import series_words
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_results import _display_cell

_HOW_MUCH = re.compile(r"얼마나|얼마|몇\s*%|몇\s*퍼센트|차이|변화|변했|증감|올랐|내렸|늘었|줄었|상승|하락|증가|감소")
_COUNT = re.compile(r"몇\s*(?:개|곳|군데|건|명|주|개국)|개수")


_COMPARE = re.compile(r"차이|비교|보다|중\s*(?:어디|어느|누가|더)|더\s*(?:비싸|싸|높|낮|많|적|크|작)")


def member_change_answer(question, summary, index, resolver=None):
    """One named row's change, or else two named rows' newest values compared ("캘리포니아와 텍사스 차이")."""
    if summary is None or index is None or _COUNT.search(question):
        return None
    modes = ([1] if _THAN.search(question) and _HOW_MUCH.search(question) else []) + ([2] if _COMPARE.search(question) else [])
    pairs = [pair for table in build_query_tables(summary) if table.complete for pair in _pairs(table)]
    for wanted in modes if pairs else ():
        try:
            if answer := asyncio.run(_answer(question, index, pairs, resolver, wanted)):
                return answer
        except Exception as exception:
            raise_for_quota_exhaustion(exception)
            return None
    return None


async def _answer(question, index, pairs, resolver, wanted=1):
    if resolver is None:
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        resolver = LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return None
    # Whole words are read too: "하와이" is a name, not "하와" with a particle.
    words = list(dict.fromkeys([*series_words(question), *re.findall(r"[가-힣]{2,}", question)]))
    readings = []
    if len(pairs) > 1:
        parents = list(dict.fromkeys(parent for _, parent, _, _ in pairs))
        found = await asyncio.gather(*(resolver.resolve(word, "column group", parents) for word in words))
        readings = [(word, parents[item.candidate_id]) for word, item in zip(words, found) if _picked(item, parents)]
        # "뉴욕 가정용" reads as Residential through 가정용: the group is named by the shortest word, and
        # 뉴욕 stays free to name the row.
        readings = [(word, parent) for word, parent in readings if not any(other != word and other in word
                                                                         for other, _ in readings)]
        pairs = [pair for pair in pairs if pair[1] in {parent for _, parent in readings}]
        if len(pairs) != 1:
            return None  # no group, or several, named: the change is not one reading
    table, parent, older, newer = pairs[0]
    label = next((column for column in table.columns if all(
        isinstance(row.values.get(column.id), str) for row in table.rows if row.values.get(column.id) not in (None, ""))), None)
    rows = [row for row in table.rows if label is not None and isinstance(row.values.get(label.id), str)
            and all(_number(row.values.get(column.id)) for column in (older, newer))]
    names = [" ".join(row.values[label.id].split()) for row in rows]
    if not rows or len(set(names)) != len(names):
        return None
    # A row written as in the source ("Hawaii") is named as written; otherwise its words are read.
    literal = [number for number, name in enumerate(names)
               if re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", question, re.I)]
    used = {word for word, _ in readings}
    rest = [word for word in words if word not in used and not any(word in other for other in used)]
    found = await asyncio.gather(*(resolver.resolve(word, " ".join(label.header.split()), names) for word in rest))
    named = [(word, item.candidate_id) for word, item in zip(rest, found) if _picked(item, names)]
    chosen = set(literal) | {number for _, number in named}
    if len(chosen) != wanted:
        return None  # not the one row a change reads, or the two rows a comparison reads
    stated = _stated([*readings, *((word, names[number]) for word, number in named)])
    if wanted == 2:
        # In the order the question names them: "캘리포니아와 텍사스" compares California with Texas.
        at = {number: min([question.find(word) for word, picked in named if picked == number] or [question.find(names[number])])
              for number in chosen}
        return _compared(table, parent, newer, label, [rows[number] for number in sorted(chosen, key=lambda item: at[item])],
                         names, rows, stated, question, index)
    row = rows[next(iter(chosen))]
    before, after = row.values[older.id], row.values[newer.id]
    style = row.number_formats.get(newer.id, "General")
    delta = after - before
    shown = lambda value: _display_cell(value, style)
    moved = "변화가 없습니다" if delta == 0 else (
        f"{shown(abs(round(delta, 10)))}" + (f"({abs(delta) / abs(before) * 100:.2f}%)" if before else "")
        + (" 올랐습니다" if delta > 0 else " 내렸습니다"))
    text = ((f"해석: {', '.join(stated)}\n" if stated else "")
            + f"{names[rows.index(row)]}의 {parent}: {_header(older)} {shown(before)} → {_header(newer)} {shown(after)}, {moved}.")
    source = {cell.reference: cell for item in index.rows if item.sheet_name == table.sheet_name for cell in item.cells}
    references = [label.header_reference, older.header_reference, newer.header_reference,
                  *(reference for reference, _ in newer.header_path),
                  *(f"{table.sheet_name}!{_letter(column)}{row.row_number}" for column in (label, older, newer))]
    return QuestionAnswer(
        question=question, answer=text, status=QuestionAnswerStatus.LIMITED, confidence=0.8,
        selected_tools=["member_column_change"],
        evidence=[_evidence(source[key]) for key in dict.fromkeys(references) if key in source],
        limitations=[f"질문의 표현을 원본으로 옮긴 해석({', '.join(stated)})이 의도와 맞는지 확인해 주세요."] if stated else [],
        verification=QuestionAnswerVerification(
            level="source_checked", checks=["source_values", "calculation", "semantic_alias_resolved"]))


def _stated(readings):
    """One wording per source name: the longest single word naming it ("하와이", not "하와"), without "와"/"과"."""
    best = {}
    for word, value in readings:
        word = re.sub(r"(?<=[가-힣]{2})(?:와|과)$", "", word)
        rank = (" " not in word, len(word) if " " not in word else -len(word))
        if value not in best or rank > best[value][0]:
            best[value] = (rank, word)
    return [f"‘{word}’ → {value}" for value, (_, word) in best.items()]


def _picked(item, values):
    return item.status == "resolved" and type(item.candidate_id) is int and 0 <= item.candidate_id < len(values)


def _compared(table, parent, newer, label, pair, names, rows, stated, question, index):
    (first, second), style = pair, pair[0].number_formats.get(newer.id, "General")
    a, b = first.values[newer.id], second.values[newer.id]
    shown = lambda value: _display_cell(value, style)
    name = lambda row: names[rows.index(row)]
    gap = (f"{name(first)}가 {name(second)}보다 {shown(abs(round(a - b, 10)))} {'높습니다' if a > b else '낮습니다'}"
           if a != b else "두 값이 같습니다")
    text = ((f"해석: {', '.join(stated)}\n" if stated else "") + f"{parent} · {_header(newer)}: {name(first)} {shown(a)}, "
            f"{name(second)} {shown(b)}. {gap}.")
    source = {cell.reference: cell for item in index.rows if item.sheet_name == table.sheet_name for cell in item.cells}
    references = [label.header_reference, newer.header_reference, *(reference for reference, _ in newer.header_path),
                  *(f"{table.sheet_name}!{_letter(column)}{row.row_number}" for row in pair for column in (label, newer))]
    return QuestionAnswer(
        question=question, answer=text, status=QuestionAnswerStatus.LIMITED, confidence=0.8,
        selected_tools=["member_column_change"],
        evidence=[_evidence(source[key]) for key in dict.fromkeys(references) if key in source],
        limitations=[f"질문의 표현을 원본으로 옮긴 해석({', '.join(stated)})이 의도와 맞는지 확인해 주세요."] if stated else [],
        verification=QuestionAnswerVerification(level="source_checked", checks=["source_values", "calculation"]))
