from dataclasses import asdict

from app.agent.contracts import (
    AgentToolContext,
    AgentToolMetadata,
    AgentToolResult,
    InvalidToolArgumentsError,
    ToolArguments,
    ToolCategory,
)
from app.agent.tools.helpers import (
    arguments_or_empty,
    bounded_integer,
    collect_evidence,
    optional_string,
)

ALLOWED_SEVERITIES = {"error", "warning"}


class FormulaRiskTool:
    metadata = AgentToolMetadata(
        name="assess_formula_risks",
        description="깨진 참조, 외부 참조, 동적 함수와 수식 패턴 위험을 조회합니다.",
        category=ToolCategory.VALIDATION,
        capabilities=("참조 오류 탐지", "패턴 불일치 탐지", "하드코딩 탐지", "영향도 조회"),
        input_schema={
            "severity": {"type": "string", "enum": ["error", "warning"]},
            "finding_limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    )

    def execute(
        self,
        context: AgentToolContext,
        arguments: ToolArguments | None = None,
    ) -> AgentToolResult:
        values = arguments_or_empty(arguments)
        severity = optional_string(values, "severity")
        if severity is not None and severity not in ALLOWED_SEVERITIES:
            raise InvalidToolArgumentsError("severity는 error 또는 warning이어야 합니다.")
        limit = bounded_integer(values, "finding_limit", 20, 100)
        summary = context.workbook.formula_risk_summary
        filtered = [
            item for item in summary.findings if severity is None or item.severity == severity
        ][:limit]
        return AgentToolResult(
            tool_name=self.metadata.name,
            summary=f"수식 위험 {summary.total_count}건 중 {len(filtered)}건을 반환했습니다.",
            data={
                "total_count": summary.total_count,
                "error_count": summary.error_count,
                "warning_count": summary.warning_count,
                "high_risk_count": summary.high_risk_count,
                "critical_risk_count": summary.critical_risk_count,
                "returned_finding_count": len(filtered),
                "findings": [asdict(item) for item in filtered],
            },
            evidence=collect_evidence(item.provenance for item in filtered),
        )
