from app.agent.contracts import (
    AgentToolContext,
    AgentToolMetadata,
    AgentToolResult,
    ToolArguments,
    ToolCategory,
)
from app.agent.tools.helpers import arguments_or_empty, collect_evidence, optional_string
from app.services.provenance import Provenance
from app.services.workbook_parsing.models import SheetSummary


class SemanticStructureTool:
    metadata = AgentToolMetadata(
        name="inspect_semantic_structure",
        description="시트와 영역의 역할, 포함·제외 판단과 근거를 조회합니다.",
        category=ToolCategory.SEMANTIC,
        capabilities=("시트 역할 분류", "영역 역할 분류", "분석 제외 사유 조회"),
        input_schema={
            "sheet_name": {
                "type": "string",
                "required": False,
                "description": "특정 시트만 조회할 때 사용할 시트명",
            }
        },
    )

    def execute(
        self,
        context: AgentToolContext,
        arguments: ToolArguments | None = None,
    ) -> AgentToolResult:
        sheet_name = optional_string(arguments_or_empty(arguments), "sheet_name")
        sheets = [
            sheet
            for sheet in context.workbook.sheets
            if sheet_name is None or sheet.name == sheet_name
        ]
        provenances = []
        for sheet in sheets:
            provenances.extend(_sheet_provenances(sheet))
        for excluded in context.workbook.excluded_sheets:
            provenances.extend(
                (excluded.analysis_inclusion.provenance, excluded.sheet_classification.provenance)
            )
        return AgentToolResult(
            tool_name=self.metadata.name,
            summary=f"분석 대상 {len(sheets)}개 시트의 의미 구조를 확인했습니다.",
            data={
                "filename": context.workbook.filename,
                "sheets": [_sheet_payload(sheet) for sheet in sheets],
                "excluded_sheets": [
                    {
                        "name": item.name,
                        "state": item.state,
                        "reason_code": item.analysis_inclusion.reason_code,
                        "reason": item.analysis_inclusion.reason,
                    }
                    for item in context.workbook.excluded_sheets
                ],
            },
            evidence=collect_evidence(provenances),
        )


def _sheet_payload(sheet: SheetSummary) -> dict[str, object]:
    classification = sheet.sheet_classification
    return {
        "name": sheet.name,
        "role": classification.role if classification else None,
        "importance": classification.importance if classification else None,
        "importance_score": classification.importance_score if classification else None,
        "confidence": classification.confidence if classification else None,
        "regions": [
            {
                "range": f"{region.start_cell}:{region.end_cell}",
                "role": region.semantic.role if region.semantic else None,
                "confidence": region.semantic.confidence if region.semantic else None,
                "included": region.analysis_inclusion.decision,
                "reason": region.analysis_inclusion.reason,
            }
            for region in sheet.regions
        ],
    }


def _sheet_provenances(sheet: SheetSummary) -> list[Provenance | None]:
    items: list[Provenance | None] = [
        sheet.analysis_inclusion.provenance,
        sheet.sheet_classification.provenance if sheet.sheet_classification else None,
    ]
    for region in sheet.regions:
        items.extend(
            (
                region.analysis_inclusion.provenance,
                region.semantic.provenance if region.semantic else None,
            )
        )
    return items
