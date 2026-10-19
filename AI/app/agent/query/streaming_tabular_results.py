"""Bounded result state; a result is published only after a complete scan."""
from collections import Counter

from app.agent.query.models import QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerVerification
from app.agent.query.streaming_tabular_numeric import NumericAccumulator
from app.agent.query.tabular_results import aggregate_text, scope_description, _label
from app.services.provenance import EvidenceKind


class StreamResult:
    def __init__(self, plan, columns):
        self.plan, self.columns = plan, columns
        self.count = self.population = self.hidden = 0
        self.rows = []
        self.numeric = {column.id: NumericAccumulator() for column in columns}
        self.frequencies = {column.id: Counter() for column in columns}
        self.blanks = Counter()

    def add(self, row):
        self.count += 1
        if self.plan.operation in {"lookup", "row_list"} and len(self.rows) < 50:
            self.rows.append(row)
        for column in self.columns:
            value = row.values[column.id]
            if self.plan.operation == "numeric_summary":
                if not self.numeric[column.id].add(value, row.number_formats.get(column.id, "General")):
                    return False
            elif self.plan.operation == "frequencies":
                if value in (None, ""):
                    self.blanks[column.id] += 1
                else:
                    self.frequencies[column.id][type(value).__name__, value] += 1
                    if len(self.frequencies[column.id]) > 1024:
                        return False
        return True

    def render(self):
        operation = self.plan.operation
        if operation == "row_count":
            return f"조건에 해당하는 행은 {self.count}건입니다.", []
        if operation == "lookup" and self.count != 1:
            return None, []
        if operation in {"lookup", "row_list"}:
            text, limitations = aggregate_text(operation, self.columns, self.rows)
            if self.count > 50:
                limitations.append(f"해당하는 {self.count}개 행 중 앞의 50개 행만 표시했습니다.")
            return text, limitations
        lines, limitations = [], []
        for column in self.columns:
            if operation == "numeric_summary":
                text = self.numeric[column.id].render(self.plan.statistic)
                if text is None:
                    return None, []
            else:
                entries = list(self.frequencies[column.id].items())
                parts = [f"‘{_label(value)}’ {count}건" for (_, value), count in entries[:30]]
                parts.append(f"빈칸 {self.blanks[column.id]}건")
                if len(entries) > 30:
                    parts.append(f"그 외 {len(entries) - 30}종 {sum(count for _, count in entries[30:])}건")
                    limitations.append("값 종류가 많아 일부 항목은 나머지 건수로 묶어 표시했습니다.")
                text = ", ".join(parts) + f" (총 {self.count}건)"
            lines.append(f"‘{column.header}’: {text}.")
        return "\n".join(lines), list(dict.fromkeys(limitations))


def result_for(plan, table, selected):
    by_id = {column.id: column for column in table.columns}
    columns = [by_id[key] for key in selected]
    if getattr(plan, "group_by", []):
        from app.agent.query.grouped_tabular_results import GroupedAccumulator
        return GroupedAccumulator(plan, table)
    if plan.operation == "row_list" and plan.order_by:
        from app.agent.query.streaming_ranked_rows import RankedRows
        return RankedRows(plan, columns)
    if plan.order_by or plan.limit is not None:
        return None
    return StreamResult(plan, columns)


def stream_answer(question, table, needed, result, *, source_scanned=True):
    text, limitations = result.render()
    if text is None:
        return None
    if result.hidden:
        text += f"\n숨겨진 {result.hidden}개 행은 제외한 결과입니다."
    evidence = []
    for column in table.columns:
        if column.id in needed:
            first = column.header_reference.rpartition("!")[2]
            last = table.reference.rpartition(":")[2]
            bottom = "".join(character for character in last if character.isdigit())
            evidence.append(QuestionAnswerEvidence(
                kind=EvidenceKind.RANGE, sheet_name=table.sheet_name, reference=f"{first}:{column.id}{bottom}",
                label=column.header,
                description=f"원본 표 전체 {result.population}개 행을 순차 대조해 조건에 맞는 {result.count}개 행을 집계",
            ))
    if not evidence:
        evidence = [QuestionAnswerEvidence(
            kind=EvidenceKind.RANGE, sheet_name=table.sheet_name, reference=table.reference, label="전체 원본 표",
            description=f"원본 표 전체 {result.population}개 행을 순차 대조해 {result.count}개 행을 집계",
        )]
    # A full column may exceed the history citation read budget. Header anchors
    # bind follow-up scope to verified source cells, never to generated prose.
    evidence.extend(QuestionAnswerEvidence(
        kind=EvidenceKind.CELL, sheet_name=table.sheet_name,
        reference=column.header_reference.rpartition("!")[2], label=column.header,
        value=column.header,
        description="전체 원본 재조회에서 직접 확인한 집계 대상 표의 열 머리글",
    ) for column in table.columns if column.id in needed or not needed and column.id not in table.hidden_columns)
    checks = ["source_values", "table_scope", "request_alignment", "calculation"]
    if source_scanned:
        checks.append("full_source_scan")
    return QuestionAnswer(
        question=question, answer=_result_scope(result.plan, table) + text,
        status="limited" if limitations else "answered", confidence=0.9 if limitations else 1,
        selected_tools=["tabular_query", "stream_original_table"] if source_scanned else ["tabular_query"],
        evidence=evidence, limitations=limitations,
        verification=QuestionAnswerVerification(level="request_checked", checks=checks),
    )


def _result_scope(plan, table):
    if not getattr(plan, "group_by", []):
        return scope_description(plan, table)
    columns = {column.id: column.header for column in table.columns}
    basic = plan.model_copy(update={"order_by": None, "limit": None})
    parts = [", ".join(columns[key] for key in plan.group_by) + "별 집계"]
    if plan.order_by or plan.limit:
        label = columns[plan.order_by] if plan.order_by else "행 개수"
        parts.append(f"{label} {'내림차순' if plan.descending else '오름차순'}")
    if plan.limit:
        parts.append(f"앞의 {plan.limit}개 그룹")
    return scope_description(basic, table) + ", ".join(parts) + "\n"
