from app.agent.contracts import (
    AgentToolContext,
    AgentToolMetadata,
    AgentToolResult,
    InvalidToolArgumentsError,
    ToolArguments,
    ToolCategory,
)
from app.agent.query.index import IndexedRow
from app.agent.query.row_search import search_rows as _search_rows
from app.agent.query.verified_evidence import (
    merge_evidence,
    priority_evidence,
    range_count_calculations,
)
from app.agent.query.verified_facts import build_verified_question_context
from app.agent.query.workbook_summary_rows import (
    is_workbook_summary_question,
    select_workbook_summary_rows,
)
from app.agent.tools.helpers import arguments_or_empty, bounded_integer, optional_string
from app.agent.tools.workbook_comparisons import (
    build_time_series_comparison,
    time_series_calculations,
)
from app.agent.tools.workbook_headers import (
    HeaderContext,
    build_header_context,
    evidence_with_header,
    header_for,
)


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
        verified = build_verified_question_context(context.workbook)
        calculations = [
            *verified["calculations"],
            *time_series_calculations(comparison),
            *range_count_calculations(context.data_index.rows, verified),
        ]
        all_evidence = [
            evidence_with_header(row, cell, headers) for row in rows for cell in row.cells
        ]
        priority = _comparison_reference_order(comparison)
        ordinary = sorted(
            all_evidence,
            key=lambda item: priority.get(
                f"{item.sheet_name}!{item.reference}", len(priority)
            ),
        )
        evidence = merge_evidence(
            priority_evidence(context.data_index.rows, verified), ordinary, 600
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
                "verified_overview": verified["overview"],
                "verified_insights": verified["insights"],
                "calculations": calculations,
                "rows": [_row_payload(row, headers) for row in rows],
            },
            evidence=evidence,
        )


def _comparison_reference_order(
    comparison: dict[str, object] | None,
) -> dict[str, int]:
    if not comparison:
        return {}
    references = {
        reference: index
        for index, key in enumerate(("start_reference", "end_reference"))
        if isinstance((reference := comparison.get(key)), str)
    }
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
                "number_format": cell.number_format,
            }
            for cell in row.cells
        ],
    }
