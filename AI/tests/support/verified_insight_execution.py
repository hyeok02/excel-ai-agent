"""Build a minimal Agent execution from source-narrative output."""

from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.verified_insight_answers import validated_verified_insight_answer
from app.services.provenance import EvidenceKind


def answer_from_verified_report(question, report, context):
    answer = validated_verified_insight_answer(
        question, execution_from_report(report, context), False,
    )
    assert answer is not None, question
    return answer


def execution_from_report(report, context):
    verified = [
        {
            "title": item.title,
            "topic": item.topic,
            "category": item.category,
            "confidence": item.confidence,
            "fact": item.fact,
            "support_references": list(item.evidence),
        }
        for item in report.insights
    ]
    result = SimpleNamespace(
        evidence=_evidence(context),
        data={"verified_insights": verified, "index_truncated": False},
    )
    return SimpleNamespace(steps=[SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED,
        result=result,
        tool_name="search_workbook_data",
    )])


def _evidence(context):
    cells = []
    for sheet in context["sheets"]:
        name, facts = sheet["name"], sheet.get("business_facts", {})
        for record in [
            *facts.get("selected_records", []), *facts.get("time_series", []),
        ]:
            cells.extend((name, cell) for cell in record.get("values", []))
        for region in facts.get("table_regions", []):
            cells.extend((name, cell) for row in region.get("rows", []) for cell in row)
        cells.extend(
            (name, cell) for row in facts.get("table_rows", []) for cell in row
        )
        for series in facts.get("horizontal_series", []):
            cells.append(
                (name, {"cell": series["label_cell"], "value": series["metric"]})
            )
            for point in series.get("points", []):
                cells.extend([
                    (name, {"cell": point["period_cell"], "value": point["period"]}),
                    (name, {"cell": point["value_cell"], "value": point["value"]}),
                ])
    unique = {
        (sheet.casefold(), str(cell["cell"]).casefold()): (sheet, cell)
        for sheet, cell in cells
    }
    return [
        AgentExecutionEvidence(
            kind=EvidenceKind.CELL,
            sheet_name=sheet,
            reference=str(cell["cell"]),
            description=str(cell.get("label") or cell.get("value") or "원본 셀"),
            value=cell.get("value"),
        )
        for sheet, cell in unique.values()
    ]
