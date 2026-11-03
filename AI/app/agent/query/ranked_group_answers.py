"""Answer "the one after X", "the N-th largest" and "the largest except X" over groups.

A model maps the wording to source fields ("쿠키" → Category = Cookies, "판매금액"
→ TotalPrice) and usually expresses the rank as a top-N limit or an exclusion
filter. The regular plan validators cannot prove such a rank from the wording, so
this path recomputes every group over the whole verified table, ranks them, and
answers with the full ranking so the reader can check the position. The answer is
marked as source-checked (values and calculation), not as request-checked: the
field mapping comes from the model and is stated in the limitations.
"""
from collections import defaultdict
from decimal import Decimal
import re

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel,
)
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_filters import filtered_rows
from app.agent.query.tabular_validation import validated_table

_AFTER = re.compile(r"다음(?:으로|가는|은|이)?|뒤를\s*잇|\b(?:after|next)\b", re.I)
_EXCEPT = re.compile(r"제외|빼고|말고|\b(?:except|excluding|other\s+than)\b", re.I)
_ORDINALS = {"두": 2, "세": 3, "네": 4, "다섯": 5, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
_NTH = re.compile(r"(\d+|두|세|네|다섯)\s*(?:번째|위|등)|\b(second|third|fourth|fifth)\b", re.I)
_TOP = re.compile(r"가장|제일|최고|최대|\b(?:most|largest|highest|top|best)\b", re.I)
_SMALL = re.compile(r"작은|적은|낮은|적게|\b(?:smallest|lowest|least|fewest)\b", re.I)
MAX_LISTED = 10
MAX_EVIDENCE = 60


def ranked_group_answer(plan, summary, index, question, targets=()):
    if plan is None or summary is None or len(plan.group_by) != 1 or plan.having:
        return None
    if plan.operation not in {"numeric_summary", "row_count"} or getattr(plan, "filter_expression", None):
        return None
    after, excepted, nth = _AFTER.search(question), _EXCEPT.search(question), _nth(question)
    top = _TOP.search(question)
    if not (after or excepted or nth or top):
        return None
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    bound = bind_tabular_plan(plan, tables[0]) if len(tables) == 1 else None
    if bound is None:
        return None
    table, group = tables[0], bound.group_by[0]
    measure = bound.column_ids[0] if bound.operation == "numeric_summary" and len(bound.column_ids) == 1 else None
    if bound.operation == "numeric_summary" and (measure is None or bound.statistic not in {"sum", "all"}):
        return None
    if not validated_table(table, index, {group, *([measure] if measure else [])}):
        return None
    anchors = [item for item in bound.filters if item.column_id == group and item.operator == "not_equals"]
    rows = filtered_rows(table, [item for item in bound.filters if item not in anchors])
    totals = _totals(rows, group, measure)
    if rows is None or totals is None or len(totals) < 2:
        return None
    ranking = sorted(totals.items(), key=lambda pair: (pair[1][0] if _SMALL.search(question) else -pair[1][0], pair[0]))
    names = [name for name, _ in ranking]
    # The model's targets name source values as written ("쿠키" → "Cookies").
    named = {str(target).casefold() for target in targets}
    anchor = [str(item.value) for item in anchors] or [name for name in names if name.casefold() in question.casefold()
                                                       or name.casefold() in named]
    if nth:
        position = nth - 1
    elif anchor and anchor[0] in names and len(anchor) == 1:
        position = names.index(anchor[0]) + 1 if after else next(
            (number for number, name in enumerate(names) if name != anchor[0]), None)
    elif top and not (after or excepted):
        position = 0
    else:
        return None
    if position is None or position >= len(names):
        return None
    return _answer(question, table, index, group, measure, ranking, position,
                   anchor[0] if anchor and not nth else None)


def _nth(question):
    found = _NTH.search(question)
    if not found:
        return None
    word = (found[1] or found[2] or "").casefold()
    return int(word) if word.isdigit() else _ORDINALS.get(word)


def _totals(rows, group, measure):
    if rows is None:
        return None
    totals = defaultdict(lambda: [Decimal(0), []])
    for row in rows:
        name, value = row.values.get(group), row.values.get(measure) if measure else 1
        if name in (None, "") or isinstance(value, bool) or not isinstance(value, (int, float)):
            if measure and value not in (None, ""):
                return None  # A non-numeric amount cannot be skipped silently.
            continue
        totals[str(name)][0] += Decimal(str(value))
        totals[str(name)][1].append(row.row_number)
    return dict(totals)


def _answer(question, table, index, group, measure, ranking, position, anchor):
    headers = {column.id: column for column in table.columns}
    metric = f"‘{headers[measure].display_header}’ 합계" if measure else "행 수"
    picked, (value, _) = ranking[position]
    listed = ", ".join(f"{number}. {name} {_number(total)}" for number, (name, (total, _))
                       in enumerate(ranking[:MAX_LISTED], 1))
    lead = (f"‘{anchor}’ 다음은 ‘{picked}’입니다" if anchor and position and ranking[position - 1][0] == anchor
            else f"{position + 1}위는 ‘{picked}’입니다")
    text = (f"{lead} ({metric} {_number(value)}). ‘{headers[group].display_header}’별 {metric} 순위: {listed}"
            + (f" 외 {len(ranking) - MAX_LISTED}개" if len(ranking) > MAX_LISTED else "") + ".")
    cells = [headers[group].header_reference, *([headers[measure].header_reference] if measure else [])]
    indexed = {f"{table.sheet_name}!{column}{row}" for column in (group, measure) if column
               for row in ranking[position][1][1]}
    source = {cell.reference: cell for row in index.rows if row.sheet_name == table.sheet_name for cell in row.cells}
    evidence = [_evidence(source[key]) for key in dict.fromkeys([*cells, *sorted(indexed)]) if key in source][:MAX_EVIDENCE]
    return QuestionAnswer(
        question=question, answer=text, status=QuestionAnswerStatus.LIMITED, confidence=0.8,
        selected_tools=["ranked_group_query"], evidence=evidence,
        limitations=[f"질문의 대상과 기준을 ‘{headers[group].display_header}’·{metric}으로 해석해 원본 전체 행으로 다시 계산했습니다."],
        verification=QuestionAnswerVerification(level=QuestionVerificationLevel.SOURCE_CHECKED,
                                                checks=["source_values", "calculation", "ranking"]),
    )


def _number(value):
    value = float(value)
    return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"
