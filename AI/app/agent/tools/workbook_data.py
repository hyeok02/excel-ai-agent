from app.agent.contracts import (
    AgentToolContext,
    AgentToolMetadata,
    AgentToolResult,
    InvalidToolArgumentsError,
    ToolArguments,
    ToolCategory,
)
from app.agent.query.comparison_scope import comparison_scope
from app.agent.query.query_rows import (
    query_scope_truncated,
    selected_question_rows,
    with_relevant_priority_rows,
)
from app.agent.query.verified_evidence import (
    merge_evidence,
    priority_evidence,
    range_count_calculations,
)
from app.agent.query.verified_facts import build_verified_question_context
from app.agent.query.intent_models import QuestionIntent
from app.agent.tools.helpers import arguments_or_empty, bounded_integer, optional_string
from app.agent.tools.workbook_comparisons import (
    build_time_series_comparison,
    time_series_calculations,
)
from app.agent.tools.workbook_evidence import (
    comparison_reference_order,
    widened_scope_evidence,
)
from app.agent.tools.workbook_lookups import build_lookups
from app.agent.tools.workbook_metric_changes import comparison_payload
from app.agent.tools.workbook_headers import (
    build_header_context,
    detect_header_rows,
    evidence_with_header,
)
from app.agent.tools.workbook_data_payload import row_payload


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
        intent = context.intent or QuestionIntent.from_keywords(context.question or query)
        found = selected_question_rows(
            context.data_index,
            context.workbook.sheets,
            query,
            limit,
            intent.whole_workbook,
        )
        summary_question, rows = found.whole_workbook, found.rows
        verified = build_verified_question_context(context.workbook)
        rows = with_relevant_priority_rows(context.data_index.rows, rows, verified)
        detected = detect_header_rows(context.data_index.rows)
        headers = build_header_context(context.data_index.rows, rows, detected)
        # 증감 방향·기간·부서 범위는 사용자가 한 질문에서 읽는다. 모델이
        # "headcount by department"처럼 바꿔 부르면 '감소'가 사라져, 도구가
        # 이미 계산해 둔 결정적 비교 답변이 통째로 꺼지고 모델 추측이 나갔다.
        # 모델이 짚은 대상을 더해 열 이름을 맞춘다. 질문이 표의 말과 다르게
        # 적혀 있어도 모델이 워크북에 적힌 이름으로 옮겨 준다.
        asked = intent.enriched(context.question or query)
        scope = comparison_scope(context.workbook, asked)
        # 시계열은 검색이 가져온 행이 아니라 그 시트 전체에서 모은다. 검색
        # 결과에 따라 비교 기간이 달라지면 같은 질문의 답이 매번 바뀐다.
        searched_sheets = {row.sheet_name for row in rows}
        series_rows = [
            row for row in context.data_index.rows if row.sheet_name in searched_sheets
        ]
        series_headers = build_header_context(
            context.data_index.rows, series_rows, detected
        )
        comparison = build_time_series_comparison(
            series_rows, series_headers, asked,
            scope.metric_group, scope.columns_by_sheet,
        )
        # 목록도 검색 결과가 아니라 시트 전체를 훑어야 한 건도 빠지지 않는다.
        lookups = build_lookups(
            series_rows, series_headers, context.data_index.rows, asked, detected
        )
        calculations = [
            *verified["calculations"],
            *time_series_calculations(comparison),
            *range_count_calculations(context.data_index.rows, verified),
        ]
        all_evidence = [
            evidence_with_header(row, cell, headers) for row in rows for cell in row.cells
        ]
        priority = comparison_reference_order(comparison)
        priority.update({
            reference: len(priority) + offset
            for offset, reference in enumerate(lookups.references)
            if reference not in priority
        })
        # 비교가 근거로 드는 셀이 검색 행 밖에 있으면, 그 하나 때문에 비교
        # 답변이 통째로 버려진다. 헤더 띠(106행)가 실제로 그렇게 빠졌다.
        all_evidence.extend(
            widened_scope_evidence(
                priority, all_evidence, series_rows, series_headers, lookups
            )
        )
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
                "brief_answer": bool(intent.brief),
                "summary_answer_allowed": bool(intent.wants_a_summary),
                "returned_row_count": len(rows),
                "index_truncated": query_scope_truncated(
                    context.data_index, rows, query, summary_question
                ),
                **comparison_payload(comparison, asked, intent.targets),
                **lookups.data,
                "verified_overview": verified["overview"],
                "verified_insights": verified["insights"],
                "calculations": calculations,
                "rows": [row_payload(row, headers) for row in rows],
            },
            evidence=evidence,
        )
