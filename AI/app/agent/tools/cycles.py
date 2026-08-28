from dataclasses import asdict

from app.agent.contracts import (
    AgentToolContext,
    AgentToolMetadata,
    AgentToolResult,
    ToolArguments,
    ToolCategory,
)
from app.agent.tools.dependency_evidence import dependency_evidence
from app.agent.tools.helpers import arguments_or_empty, bounded_integer


class CircularReferenceTool:
    metadata = AgentToolMetadata(
        name="detect_circular_references",
        description="수식 참조 그래프에서 순환 참조와 관련 셀을 조회합니다.",
        category=ToolCategory.VALIDATION,
        capabilities=("순환 참조 탐지", "순환 셀 추적", "관련 시트 확인"),
        input_schema={
            "cycle_limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "required": False,
            }
        },
    )

    def execute(
        self,
        context: AgentToolContext,
        arguments: ToolArguments | None = None,
    ) -> AgentToolResult:
        summary = context.workbook.dependency_summary
        limit = bounded_integer(arguments_or_empty(arguments), "cycle_limit", 10, 20)
        cycles = summary.cycles[:limit]
        message = (
            f"순환 참조 {summary.cycle_count}건을 확인했습니다."
            if summary.cycle_count
            else "순환 참조가 발견되지 않았습니다."
        )
        return AgentToolResult(
            tool_name=self.metadata.name,
            summary=message,
            data={
                "cycle_count": summary.cycle_count,
                "cyclic_node_count": summary.cyclic_node_count,
                "returned_cycle_count": len(cycles),
                "cycles": [asdict(cycle) for cycle in cycles],
            },
            evidence=dependency_evidence(
                node for cycle in cycles for node in cycle.nodes
            ),
        )
