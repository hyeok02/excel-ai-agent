"""One named member's share of a column's total, as a last resort.

"Bars 카테고리가 전체 판매금액에서 차지하는 비중은?" names a value written in the source (Bars, a
Category) and a measure in other words (판매금액 → TotalPrice). The member's sum and the column's
total are computed over the whole verified table, and the reading of the measure is stated.
"""
import asyncio
import re
from decimal import Decimal

from app.agent.query.cell_display import _display_cell
from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.references import normalize_reference
from app.agent.query.series_topic_names import series_words
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.tabular_subtotal_rows import typed_total
from app.agent.query.tabular_validation import validated_table

_SHARE = re.compile(r"비중|차지|점유|구성비|\b(?:share|proportion)\b", re.I)


def member_share_answer(question, summary, index, resolver=None):
    if summary is None or index is None or not _SHARE.search(question):
        return None
    found = []
    for table in build_query_tables(summary):
        if not table.complete:
            continue
        for column in table.columns:
            values = {value for row in table.rows if isinstance(value := row.values.get(column.id), str) and value.strip()}
            found += [(table, column, value) for value in values if len(values) > 1 and value_matches(question, value)]
    # The member is named as written; of the tables holding it, the one whose measure the question names.
    readable = []
    for table, member_column, member in found:
        numeric = [column for column in table.columns if column.id != member_column.id and all(
            isinstance(row.values.get(column.id), (int, float)) and not isinstance(row.values.get(column.id), bool)
            for row in table.rows)]
        measure, word = _measure(question, numeric, resolver)
        if measure is not None and validated_table(table, index, {member_column.id, measure.id}):
            readable.append((table, member_column, member, measure, word))
    if len(readable) != 1:
        return None  # no member, or several, named with a measure
    table, member_column, member, measure, word = readable[0]
    rows = list(table.rows)
    if (total_row := typed_total(rows, [measure.id])) is not None:
        rows.remove(total_row)
    whole = sum(Decimal(str(row.values[measure.id])) for row in rows)
    part = sum(Decimal(str(row.values[measure.id])) for row in rows if row.values.get(member_column.id) == member)
    if not whole:
        return None
    style = rows[0].number_formats.get(measure.id, "General")
    spec = parse_number_format(style)
    shown = lambda value: (f"{spec.prefix}{float(value):,.{0 if value == value.to_integral_value() else 2}f}{spec.suffix}"
                           if spec.mode == "raw" else _display_cell(float(value), style))  # $10,535.57
    reading = f"해석: ‘{word}’ → {measure.header}\n" if word else ""
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    cited = [cell for reference in (member_column.header_reference, measure.header_reference)
             if (cell := cells.get(normalize_reference(reference))) is not None]
    text = (f"{reading}{member_column.header} = {member}의 {measure.header} 합계 {shown(part)}는 전체 {shown(whole)}의 "
            f"{part / whole * 100:.2f}%입니다.")
    return QuestionAnswer(
        question=question, answer=text, status=QuestionAnswerStatus.LIMITED, confidence=0.8,
        selected_tools=["tabular_query", "member_share"], evidence=[_evidence(cell) for cell in cited],
        limitations=[f"‘{word}’를 {measure.header}로 읽은 해석이 의도와 맞는지 확인해 주세요."] if word else [],
        verification=QuestionAnswerVerification(level="source_checked", checks=["source_values", "calculation"]))


def _measure(question, numeric, resolver):
    """(column, word read as it) for the one measure the question names; the word is "" when written as is."""
    written = [column for column in numeric if re.search(rf"(?<![A-Za-z0-9_]){re.escape(column.header)}(?![A-Za-z0-9_])",
                                                         question, re.I)]
    if len(written) == 1:
        return written[0], ""
    if written or not numeric:
        return None, ""
    if resolver is None:
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        resolver = LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return None, ""
    headers = [column.header for column in numeric]
    words = series_words(question)
    try:
        results = asyncio.run(_read(resolver, words, headers))
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None, ""
    named = {(word, headers[item.candidate_id]) for word, item in zip(words, results) if item.status == "resolved"
             and type(item.candidate_id) is int and 0 <= item.candidate_id < len(headers)}
    picked = {header for _, header in named}
    if len(picked) != 1:
        return None, ""
    word = min((word for word, _ in named), key=len)
    return next(column for column in numeric if column.header == next(iter(picked))), word


async def _read(resolver, words, headers):
    return await asyncio.gather(*(resolver.resolve(word, "column name", headers) for word in words))
