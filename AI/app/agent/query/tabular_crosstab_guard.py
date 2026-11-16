"""A cross-tab answer must agree with the detail table it summarizes, for the measure asked.

"동부 지역 판매금액" can be planned as the East column of a Region cross-tab of quantities
(9,656), while 판매금액 names TotalPrice in the detail table where Region = East ($21,524.36).
Only a computed column named after another table's value is checked: when a question word
names a numeric column of that table, its figure for the value must appear in the answer.
"""
import asyncio
import re

from app.agent.query.excel_number_formats import parse_number_format, scaled_value
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_fixed_groups import without_fixed_groups  # noqa: F401 (one service import)
from app.agent.query.tabular_routing import planned_tabular_answer
from app.agent.query.tabular_member_rows import member_ranking
from app.agent.query.tabular_population_context import MIXED_ROLES, OVERLAPPING_TOTALS
from app.agent.query.tabular_translated_filters import candidate_words, translated_filter_answer

ANOTHER_MEASURE = "요약표의 열이 질문한 항목과 다른 값을 담고 있어, 요약표 값으로 답하지 않았습니다."


async def checked_tabular_answer(intent, summary, data_index, question, resolver=None):
    tabular = await asyncio.to_thread(planned_tabular_answer, intent, summary, data_index, question)
    if tabular is not None and tabular.answer in {MIXED_ROLES, OVERLAPPING_TOTALS}:  # groups ranked with members
        return await member_ranking(intent.tabular_query, summary, data_index, question) or tabular
    if (tabular is None or tabular.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
            or tabular.selected_tools != ["tabular_query"]
            or not await _disagrees(question, summary, intent.tabular_query, tabular.answer, resolver)):
        return tabular
    return _another_measure(question)


async def checked_translated_answer(question, summary, data_index, intent, resolver=None):
    """The same check for a plan read through translated words ("동부" → the East column of a quantity
    cross-tab while 판매금액 is TotalPrice): its refusal goes on to the cross-tab replan."""
    answer = await translated_filter_answer(question, summary, data_index, intent)
    if (answer is None or "member_rows" in answer.selected_tools
            or not await _disagrees(question, summary, intent.tabular_query, answer.answer, resolver, confirmed=True)):
        return answer
    return _another_measure(question)


def _another_measure(question):
    return QuestionAnswer(question=question, answer=ANOTHER_MEASURE, status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
                          confidence=0, selected_tools=["tabular_query"], evidence=[], limitations=[ANOTHER_MEASURE])


def detail_tables(summary, plan):
    """Tables holding the computed cross-tab column's name as a value: where its rows are recorded."""
    tables = build_query_tables(summary)
    table = next((item for item in tables if item.id == plan.table_id), None)
    headers = {_normal(column.header) for column in table.columns if column.id in plan.column_ids} if table else set()
    return [{"table_id": other.id, "column": dimension.header} for other in tables if table and other.id != table.id
            for dimension in other.columns if any(_normal(row.values.get(dimension.id)) in headers for row in other.rows)]


def _normal(value):
    return " ".join(str(value).casefold().split())


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


async def _disagrees(question, summary, plan, answer, resolver, confirmed=False):
    """confirmed: the shown figure must also be another measure's total over several detail rows."""
    if plan is None or plan.operation not in {"numeric_summary", "lookup"}:
        return False
    tables = build_query_tables(summary)
    table = next((item for item in tables if item.id == plan.table_id), None)
    if table is None:
        return False
    headers = {_normal(column.header) for column in table.columns if column.id in plan.column_ids}
    details = [(other, dimension.id, rows) for other in tables if other.id != table.id and other.complete
               for dimension in other.columns
               if (rows := [row for row in other.rows if _normal(row.values.get(dimension.id)) in headers])]
    words = [word for word in candidate_words(question, table) if re.search(r"[가-힣]", word)]
    if not details or not words:
        return False
    if resolver is None:
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        resolver = LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return False
    shown = [float(item.replace(",", "")) for item in re.findall(r"-?\d[\d,]*(?:\.\d+)?", answer)]
    for other, _, rows in details:
        if confirmed and len(rows) < 2:
            continue  # one row of another table is the same entity, not the records a cross-tab sums
        measures = [column for column in other.columns
                    if any(_number(row.values.get(column.id)) for row in rows)
                    and all(_number(row.values.get(column.id)) or row.values.get(column.id) is None for row in rows)]
        if not measures:
            continue
        labels = [column.header for column in measures]
        try:
            results = await asyncio.gather(*(resolver.resolve(word, "column name", labels) for word in words))
        except Exception as exception:
            raise_for_quota_exhaustion(exception)
            return False
        for result in results:
            if result.status != "resolved" or type(result.candidate_id) is not int or not 0 <= result.candidate_id < len(measures):
                continue
            column = measures[result.candidate_id]
            values = [row.values[column.id] for row in rows if _number(row.values.get(column.id))]
            if plan.operation == "lookup" and len(values) != 1:
                continue
            if not _shows(shown, column, values) and (not confirmed or any(
                    _shows(shown, other_column, [row.values[other_column.id] for row in rows
                                                 if _number(row.values.get(other_column.id))])
                    for other_column in measures if other_column is not column)):
                return True
    return False


def _shows(shown, column, values):
    expected = sum(values)
    formats = [parse_number_format(item) for item in column.number_formats[:1]]
    candidates = {expected, *(scaled_value(expected, spec) for spec in formats)}
    return any(abs(number - value) <= max(abs(value) * 0.005, 0.01) for number in shown for value in candidates)
