"""Rank the groups of an outline table by their own total rows.

Table 1.2 writes a sector once ("Domestic transport") over its unlabelled sources, then
"Domestic transport total". The value on the sector's own row is its first source's (Passenger
cars 59.5); the sector's value is its total row (110.4). "배출량이 가장 많은 부문은?" ranks those
total rows, one per heading, and never a grand total.
"""
import re

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.references import normalize_reference


def outline_ranking(plan, table, label, metric, data_index, question, shown, letter):
    names = lambda row: " ".join(str(row.values.get(label.id) or "").split())
    by_name = {names(row).casefold(): row for row in table.rows if names(row)}
    groups = []
    for row in table.rows:
        heading = names(row)
        total = by_name.get(f"{heading} total".casefold()) if heading and not re.search(r"\btotal\b", heading, re.I) else None
        if total is not None and isinstance(total.values.get(metric.id), (int, float)):
            groups.append((heading, total))
    if len(groups) < 2:
        return None  # not an outline with a total per heading: the refusal stands
    ordered = sorted(groups, key=lambda item: item[1].values[metric.id], reverse=plan.descending)
    top = ordered[:plan.limit]
    if len(ordered) > len(top) and ordered[len(top)][1].values[metric.id] == top[-1][1].values[metric.id]:
        return None  # a tie at the cut is not decided by row order
    cells = {normalize_reference(cell.reference): cell for row in data_index.rows for cell in row.cells}
    cited = [cells.get(normalize_reference(reference)) for reference in
             [label.header_reference, metric.header_reference,
              *(f"{table.sheet_name}!{letter(column)}{total.row_number}" for _, total in top for column in (label, metric))]]
    if None in cited:
        return None
    order = "높은" if plan.descending else "낮은"
    note = (f"해석: {' '.join(label.header.split())}의 각 그룹 값은 그 그룹의 합계 행(‘… total’)으로 읽었습니다 "
            f"(그룹 {len(groups)}개)")
    body = (f"{metric.display_header} 기준 가장 {order} 그룹: {top[0][0]} {shown(top[0][1], metric)}" if len(top) == 1
            else f"{metric.display_header} 기준 {order} 순:\n" + "\n".join(
                f"{place}. {name}: {shown(total, metric)}" for place, (name, total) in enumerate(top, 1)))
    return QuestionAnswer(
        question=question, answer=f"{note}\n{body}", status=QuestionAnswerStatus.LIMITED, confidence=0.8,
        selected_tools=["tabular_query", "outline_groups"], evidence=[_evidence(cell) for cell in dict.fromkeys(cited)],
        limitations=["그룹 이름 행의 값은 첫 하위 항목의 값이라, 그룹마다 ‘… total’ 행의 값으로 비교했습니다."],
        verification=QuestionAnswerVerification(level="source_checked", checks=["source_values", "ranking"]))
