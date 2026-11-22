"""The answers of a GPT-chosen calculation: the calculation stated, its results, the cells read."""
import re
from datetime import date

from app.agent.query.cell_display import _display_cell
from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.gpt_calc_cells import result_style, written
from app.agent.query.gpt_calc_draft_check import cites_only_seen_cells, numbers_hold
from app.agent.query.gpt_calc_labels import _condition, _formula_name, plain
from app.agent.query.gpt_calc_planner import column_name
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.references import normalize_reference

MAX_LINES = 20
_PERCENT = re.compile(r"\*\s*100\s*\)?\s*$")  # "… / [B4] * 100" is a percentage
_AGGREGATES = {"sum": "합계", "mean": "평균", "median": "중앙값", "count": "건수", "count_distinct": "서로 다른 값의 수",
               "min": "최솟값", "max": "최댓값", "ratio": "비율"}
_CHECKED = ("GPT가 정한 계산 방식(맨 위)을 코드가 원본 값으로 계산한 결과입니다. "
            "계산 방식이 질문 의도와 맞는지 확인해 주세요.")
_REFUSAL = re.compile(r"확인할 수 없|알 수 없|확인이 어렵|확인되지 않|포함되어 있지 않|제공되지 않|명시되어 있지 않|"
                      r"판단할 수 없|답할 수 없|찾을 수 없")


def shown(value, style):
    if style == "date":  # a day kept as its ordinal: 2025-12-31
        return date.fromordinal(int(value)).isoformat()
    if style == "ratio%":
        return f"{value:,.2f}%"
    if style == "#,##0" or style == "General" and float(value).is_integer():
        return f"{value:,.0f}"
    spec = parse_number_format(style)
    if spec.mode == "raw":  # "$"General: the source's sign, with separators and cents
        return f"{spec.prefix}{value:,.2f}{spec.suffix}" if spec.prefix or spec.suffix else plain(round(value, 2))
    return _display_cell(round(value, 4), style)


def table_answer(question, plan, table, result, style, cells):
    calc = plan.table
    name = column_name(result.columns[-1]) if calc.measure else "행"  # the measure is read last
    name, style = (_formula_name(calc.row_formula, table), "General" if "/" in calc.row_formula else style) \
        if calc.row_formula else (name, "date" if result.dated else style)  # a weighted mean is not in a count's format
    name = " + ".join([name, *(item for item in calc.add if item != calc.measure)]) if calc.add and calc.measure else name
    name += f" - {calc.subtract}" if calc.subtract else ""
    name = f"|{name}|" if calc.absolute else name
    lines, listing = [f"계산 방식: {plan.method}"], False
    if conditions := [_condition(item) for item in calc.filters if item.value.strip() != "*"]:
        lines.append("적용 조건: " + ", ".join(conditions))  # what "2020년 이후" was read as: 입사일 ≥ 2021-01-01
    groups = result.groups
    if not groups:
        lines.append("조건에 맞는 항목이 없습니다.")
    elif result.parts:  # a share of the filtered rows in all of them, with both counts
        part, whole = result.parts
        lines.append(f"비율: {shown(groups[0][1], style)} ({name if calc.measure else '행 수'} {plain(part)} / 전체 {plain(whole)})")
    elif result.changes:  # each store's first and last month, and which grew more
        lines += [f"· {item}: {first} {shown(a, style)} → {last} {shown(b, style)}, {'+' if b >= a else '-'}"
                  f"{shown(abs(b - a), style)}" + (f" ({(b - a) / abs(a) * 100:+.2f}%)" if a else "")
                  for item, first, a, last, b in result.changes]
    elif len(groups) == 1 and groups[0][0] == "전체":
        word = "값" if result.rows == 1 and calc.aggregate in {"sum", "mean", "min", "max"} else _AGGREGATES[calc.aggregate]
        lines.append(f"{name} {word}: {shown(groups[0][1], style)}")  # one row read is its value, not a 합계
    else:
        if result.mean is not None:
            lines.append(f"그룹 평균 {shown(result.mean, style)}보다 {'높은' if calc.pick == 'above_mean' else '낮은'} "
                         f"항목 {len(groups)}개:")
        elif calc.pick == "all":  # "몇 개 도시": the number of groups is stated before them
            lines.append(f"{' · '.join(result.grouped)} {len(groups)}개:")
        listing = calc.aggregate == "count" and all(value == 1 for _, value, _ in groups)  # records named, not counted
        for number, (label, value, share) in enumerate(groups[:MAX_LINES], 1):
            prefix = f"{calc.n}위 " if calc.pick == "nth" else f"{number}. " if calc.order != "none" else "· "
            lines.append(f"{prefix}{label}" + ("" if listing else f": {shown(value, style)}")
                         + (f" ({share:.2f}%" + (f", {result.sizes[label]:,}건" if label in result.sizes else "")
                            + ")" if share is not None else ""))
        if len(groups) > MAX_LINES:
            lines.append(f"외 {len(groups) - MAX_LINES}개")
        if len(groups) == 2 and calc.period != "none" and calc.pick == "all":  # 2022 → 2023
            (first, a, _), (second, b, _) = groups
            change = f" ({(b - a) / abs(a) * 100:+.2f}%)" if a else ""
            lines.append(f"{first} → {second}: {'+' if b >= a else '-'}{shown(abs(b - a), style)}{change}")
        elif len(groups) == 2 and calc.pick == "all" and calc.aggregate in {"sum", "mean", "median"}:  # 강남점 vs 홍대점
            (first, a, _), (second, b, _) = groups
            lines.append(f"차이({first} - {second}): {'-' if a < b else ''}{shown(abs(a - b), style)}")
    lines += [f"{label}: {plain(value)}" for label, value in result.extras]  # 초과 금액 합계 beside the count
    if result.then is not None:  # "상위 3일의 평균": the groups picked, then their mean
        lines.append(f"위 {len(groups)}개의 {_AGGREGATES[calc.then]}: {shown(result.then, style)}")
    if result.by_column:  # the columns added, each shown: a trend over year columns reads from them
        lines.append("열별 값: " + " · ".join(f"{label} {shown(value, style)}" for label, value in result.by_column))
    lines.append(f"(원본 ‘{table.sheet_name}’ 표의 {result.rows:,}개 행으로 계산"
                 + (f", 상위 구분 행 {len(result.skipped)}개 제외: {', '.join(result.skipped[:3])}"
                    + (" 등" if len(result.skipped) > 3 else "") if result.skipped else "") + ")")
    cited = [cells.get(normalize_reference(column.header_reference)) for column in result.columns]
    return _answer(question, "\n".join(lines), [cell for cell in cited if cell is not None], listing)


def cells_answer(question, plan, computed):
    keep = plan.cells.keep
    kept = [(item, found) for item, found in computed if keep == "all" or keep == "positive" and found[0] > 0
            or keep == "negative" and found[0] < 0 or keep in {"above", "below"} and plan.cells.threshold is None]
    if keep in {"above", "below"} and plan.cells.threshold is not None:  # "60%를 넘은 해"
        kept = [(item, found) for item, found in computed
                if (found[0] > plan.cells.threshold if keep == "above" else found[0] < plan.cells.threshold)]
    if keep in {"max", "min"}:
        kept = [(max if keep == "max" else min)(computed, key=lambda pair: pair[1][0])]
    lines = [f"계산 방식: {plan.method}"]
    if not kept:
        lines.append(f"조건에 맞는 항목이 없습니다 (계산한 {len(computed)}개 모두 해당 없음).")
    elif keep in {"positive", "negative", "above", "below"}:
        lines.append(f"해당 항목 {len(kept)}개 (계산한 {len(computed)}개 중):")
    for item, (value, used) in (kept or computed)[:MAX_LINES]:
        style = result_style(item.expression, used)  # a difference of rates is in points: 0.7%p
        result = (_display_cell(value, style) + ("p" if "%" in style and re.search(r"\]\s*-", item.expression) else "")
                  if style not in (None, "General") else plain(value) + ("%" if _PERCENT.search(item.expression) else ""))
        lines.append(f"· {item.label}: {written(item.expression, used)} = {result}")
    used = [cell for _, (_, items) in computed for _, cell in items]
    return _answer(question, "\n".join(lines), list(dict.fromkeys(used)))


def _answer(question, text, cited, listing=False):
    return QuestionAnswer(
        question=question, answer=text, status=QuestionAnswerStatus.LIMITED, confidence=0.6,
        selected_tools=["gpt_calculation"], evidence=[_evidence(cell) for cell in cited], limitations=[_CHECKED],
        verification=QuestionAnswerVerification(level="source_checked",
                                                checks=["source_values", *([] if listing else ["calculation"]),
                                                        "gpt_calculation_plan"]))


def unverified_draft(question, answer, draft, values, references=None):
    """GPT's own answer when it answers rather than declines and code recomputes each of its numbers
    from the source values it was shown; else None."""
    first = re.split(r"(?<=[.다])\s", draft.answer.strip(), maxsplit=1)[0]
    declined = _REFUSAL.search(first) or draft.claims and all(claim.kind == "unknown" for claim in draft.claims)
    if declined or draft.confidence < 0.5 or not numbers_hold(draft.answer, values) \
            or references is not None and not cites_only_seen_cells(draft.evidence, references):
        return None
    return QuestionAnswer(
        question=question, answer=f"[GPT 답변 · 수치 검산] {draft.answer.strip()}", status=QuestionAnswerStatus.LIMITED,
        confidence=min(draft.confidence, 0.5), selected_tools=[*answer.selected_tools, "checked_generation"],
        evidence=[], limitations=["GPT가 원본 값으로 쓴 수치를 코드가 다시 계산해 맞는지 확인했습니다. "
                                  "어떤 값을 골라 계산했는지는 원본과 대조해 주세요."])
