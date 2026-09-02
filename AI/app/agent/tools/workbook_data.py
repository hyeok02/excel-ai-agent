from app.agent.contracts import (
    AgentToolContext,
    AgentToolMetadata,
    AgentToolResult,
    InvalidToolArgumentsError,
    ToolArguments,
    ToolCategory,
)
from app.agent.query.index import IndexedRow
from app.agent.query.workbook_summary_rows import (
    is_workbook_summary_question,
    select_workbook_summary_rows,
)
from app.agent.tools.helpers import arguments_or_empty, bounded_integer, optional_string
from app.agent.tools.workbook_comparisons import build_time_series_comparison
from app.agent.tools.workbook_headers import (
    HeaderContext,
    build_header_context,
    evidence_with_header,
    header_for,
)
from app.agent.query.search_terms import relevance, search_terms
PRECEDING_ROW_COUNT = 3
FOLLOWING_ROW_COUNT = 8


class WorkbookDataSearchTool:
    metadata = AgentToolMetadata(
        name="search_workbook_data",
        description="질문과 관련된 원본 셀 값, 행과 수식을 검색합니다.",
        category=ToolCategory.SEMANTIC,
        capabilities=("셀 값 검색", "관련 행 조회", "원본 셀 근거 제공"),
        input_schema={
            "query": {"type": "string", "required": True},
            "row_limit": {"type": "integer", "minimum": 1, "maximum": 40},
        },
    )

    def execute(
        self, context: AgentToolContext, arguments: ToolArguments | None = None
    ) -> AgentToolResult:
        if context.data_index is None:
            raise InvalidToolArgumentsError("원본 셀 검색 인덱스가 준비되지 않았습니다.")
        values = arguments_or_empty(arguments)
        query = optional_string(values, "query")
        if query is None:
            raise InvalidToolArgumentsError("query는 필수입니다.")
        limit = bounded_integer(values, "row_limit", 24, 40)
        summary_question = is_workbook_summary_question(query)
        rows = (
            select_workbook_summary_rows(
                context.data_index.rows, context.workbook.sheets, limit
            )
            if summary_question
            else _search_rows(context.data_index.rows, query, limit)
        )
        headers = build_header_context(context.data_index.rows, rows)
        comparison = build_time_series_comparison(rows, headers, query)
        all_evidence = [
            evidence_with_header(row, cell, headers) for row in rows for cell in row.cells
        ]
        priority = _comparison_reference_order(comparison)
        evidence = tuple(
            sorted(
                all_evidence,
                key=lambda item: priority.get(
                    f"{item.sheet_name}!{item.reference}", len(priority)
                ),
            )[:600]
        )
        return AgentToolResult(
            tool_name=self.metadata.name,
            summary=f"질문과 관련된 원본 행 {len(rows)}개를 조회했습니다.",
            data={
                "query": query,
                "workbook_summary_query": summary_question,
                "returned_row_count": len(rows),
                "index_truncated": context.data_index.truncated,
                "time_series_comparison": comparison,
                "rows": [_row_payload(row, headers) for row in rows],
            },
            evidence=evidence,
        )


def _search_rows(rows: tuple[IndexedRow, ...], query: str, limit: int) -> list[IndexedRow]:
    terms = search_terms(query)
    scored = [(relevance(row, terms), index) for index, row in enumerate(rows)]
    anchors = [
        index
        for score, index in sorted(scored, key=lambda item: (-item[0], item[1]))
        if score > 0
    ][:6]
    if not anchors:
        return sorted(rows, key=lambda row: len(row.cells), reverse=True)[: min(limit, 20)]
    selected: set[int] = set()
    ordered: list[int] = []
    for anchor in anchors:
        sheet_name = rows[anchor].sheet_name
        start = max(0, anchor - PRECEDING_ROW_COUNT)
        for index in range(start, min(len(rows), anchor + FOLLOWING_ROW_COUNT + 1)):
            if rows[index].sheet_name != sheet_name:
                continue
            if index not in selected:
                selected.add(index)
                ordered.append(index)
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break
    return [rows[index] for index in ordered[:limit]]


def _comparison_reference_order(
    comparison: dict[str, object] | None,
) -> dict[str, int]:
    if not comparison:
        return {}
    references = {}
    groups = (comparison.get("largest_absolute_changes"), comparison.get("metrics"))
    for metrics in groups:
        if not isinstance(metrics, list):
            continue
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            for key in ("start_reference", "end_reference"):
                reference = metric.get(key)
                if isinstance(reference, str) and reference not in references:
                    references[reference] = len(references)
    return references


def _row_payload(row: IndexedRow, headers: HeaderContext) -> dict[str, object]:
    return {
        "sheet_name": row.sheet_name,
        "row_number": row.row_number,
        "cells": [
            {
                "reference": cell.reference,
                "header": header_for(headers, row.sheet_name, row.row_number, cell.address),
                "value": cell.value,
                "formula": cell.formula,
            }
            for cell in row.cells
        ],
    }
