"""A ranking over a column mixing groups with their members ranks only the rows the question asks about.

"가정용 전기요금이 가장 높은 주는?" is planned over 'Census Division and State', whose rows are
census divisions, their states and the U.S. total; ranking them together is refused, since a
division restates its states. A bounded call reads which labels are the kind of record the
question ranks (주 → the states), choosing only among the column's own labels. The ranking is
then computed here from the source cells, and the reading is stated with the answer.
"""
import re

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.references import normalize_reference
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables

MAX_LABELS = 300
MAX_SHOWN_EXCLUDED = 12


async def member_ranking(plan, summary, data_index, question, classifier=None):
    if (plan is None or plan.operation != "row_list" or not plan.order_by or not plan.limit or plan.filters
            or plan.filter_expression is not None or plan.group_by or plan.having or plan.relative_rank):
        return None
    table = next((item for item in build_query_tables(summary) if item.id == plan.table_id), None)
    plan = bind_tabular_plan(plan, table) if table is not None and table.complete else None
    metric = next((column for column in table.columns if column.id == plan.order_by), None) if plan else None
    label = _label_column(table, plan) if metric is not None else None
    if label is None:
        return None
    rows = [row for row in table.rows if _number(row.values.get(metric.id))
            and isinstance(row.values.get(label.id), str) and row.values[label.id].strip()]
    labels = [" ".join(row.values[label.id].split()) for row in rows]
    # An outline label ("Domestic transport" over Passenger cars, HGVs, …) heads the unlabelled rows
    # below it: the value on its own row is its first member's, not the group's.
    if any(_number(row.values.get(metric.id)) and row.values.get(label.id) in (None, "") for row in table.rows):
        from app.agent.query.tabular_outline_groups import outline_ranking
        return outline_ranking(plan, table, label, metric, data_index, question, _shown, _letter)
    if not rows or len(labels) > MAX_LABELS or len(set(labels)) != len(labels):
        return None
    if classifier is None:
        from app.agent.query.row_kind_classifier import LangChainRowKindClassifier
        classifier = LangChainRowKindClassifier.from_environment()
    if classifier is None:
        return None
    try:
        reading = await classifier.classify(question, " ".join(label.header.split()), labels)
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None
    chosen = sorted({number for number in reading.candidate_ids if 0 <= number < len(rows)})
    if reading.status != "selected" or not chosen or len(chosen) == len(rows):
        return None  # nothing read, or no group row to leave out: the refusal stands
    ordered = sorted(chosen, key=lambda number: rows[number].values[metric.id], reverse=plan.descending)
    top = ordered[:plan.limit]
    if len(ordered) > len(top) and rows[ordered[len(top)]].values[metric.id] == rows[top[-1]].values[metric.id]:
        return None  # a tie at the cut is not decided by row order
    cells = {normalize_reference(cell.reference): cell for row in data_index.rows for cell in row.cells}
    cited = [cells.get(normalize_reference(reference)) for reference in
             [label.header_reference, metric.header_reference, *(source for source, _ in metric.header_path),
              *(f"{table.sheet_name}!{column}{rows[number].row_number}" for number in top
                for column in (_letter(label), _letter(metric)))]]
    if None in cited:
        return None
    excluded = [labels[number] for number in range(len(rows)) if number not in set(chosen)]
    kind = reading.kind.strip() or "질문한 대상"
    shown = ", ".join(excluded[:MAX_SHOWN_EXCLUDED]) + (f" 외 {len(excluded) - MAX_SHOWN_EXCLUDED}개"
                                                         if len(excluded) > MAX_SHOWN_EXCLUDED else "")
    note = f"해석: {kind} → {' '.join(label.header.split())}의 {len(chosen)}개 행 (제외: {shown})"
    order = "높은" if plan.descending else "낮은"
    body = (f"{metric.display_header} 기준 가장 {order} {kind}: {labels[top[0]]} {_shown(rows[top[0]], metric)}"
            if len(top) == 1 else f"{metric.display_header} 기준 {order} 순:\n" + "\n".join(
                f"{place}. {labels[number]}: {_shown(rows[number], metric)}" for place, number in enumerate(top, 1)))
    return QuestionAnswer(
        question=question, answer=f"{note}\n{body}",
        status=QuestionAnswerStatus.LIMITED, confidence=0.8, selected_tools=["tabular_query", "member_rows"],
        evidence=[_evidence(cell) for cell in dict.fromkeys(cited)],
        limitations=[f"어떤 행이 {kind}인지는 이름으로 판단한 해석입니다. 제외한 행({shown})이 맞는지 확인해 주세요."],
        verification=QuestionAnswerVerification(level="source_checked",
                                                checks=["source_values", "ranking", "semantic_alias_resolved"]))


def _label_column(table, plan):
    named = [column for column in table.columns if column.id in plan.identity_column_ids]
    for column in named or table.columns:
        values = [row.values.get(column.id) for row in table.rows if row.values.get(column.id) not in (None, "")]
        if values and all(isinstance(value, str) for value in values):
            return column
    return None


def _letter(column):
    return re.sub(r"\d+$", "", column.header_reference.rsplit("!", 1)[-1]).replace("$", "")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _shown(row, column):
    style = row.number_formats.get(column.id, "")
    places = len(style.split(".", 1)[1].rstrip("%")) if "." in style and style[:1] in "0#" else None
    value = row.values[column.id]
    return f"{value:,.{places}f}" if places is not None and places <= 6 else f"{value:,}"
