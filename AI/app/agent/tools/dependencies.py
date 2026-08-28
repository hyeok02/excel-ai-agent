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


class FormulaDependencyTool:
    metadata = AgentToolMetadata(
        name="trace_formula_dependencies",
        description="수식 참조 그래프와 서로 연결된 계산 군집을 조회합니다.",
        category=ToolCategory.DEPENDENCY,
        capabilities=("BFS 계산 군집 조회", "시트 간 참조 추적", "영향 관계 확인"),
        input_schema={
            "cluster_limit": {
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
        limit = bounded_integer(arguments_or_empty(arguments), "cluster_limit", 5, 20)
        clusters = summary.clusters[:limit]
        return AgentToolResult(
            tool_name=self.metadata.name,
            summary=f"{summary.cluster_count}개 계산 군집과 {summary.edge_count}개 참조를 확인했습니다.",
            data={
                "node_count": summary.node_count,
                "edge_count": summary.edge_count,
                "cross_sheet_edge_count": summary.cross_sheet_edge_count,
                "cluster_count": summary.cluster_count,
                "returned_cluster_count": len(clusters),
                "clusters": [asdict(cluster) for cluster in clusters],
            },
            evidence=dependency_evidence(
                node for cluster in clusters for node in cluster.nodes
            ),
        )
