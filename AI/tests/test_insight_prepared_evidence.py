"""Production builders and consumers share one request-local reference snapshot."""
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.services.insights.models import WorkbookInsight
from app.services.insights.narratives import workbook_overview
from app.services.insights.verification import validator
from app.services.insights.verification.reference_matching import resolve_references
from app.services.insights.verification.validation_index import (
    agent_evidence_index, workbook_evidence_index,
)
from app.services.provenance import EvidenceKind


def _context():
    return {"sheets": [{"name": "Source", "formula_samples": [
        {"cell": "C2", "formula": "=B2*2"},
    ], "business_facts": {"selected_records": [{"location": "A1:B3", "values": [
        {"cell": cell, "value": value} for cell, value in (
            ("A1", "항목"), ("B1", "금액"), ("A2", "매출"),
            ("B2", 100), ("A3", "비용"), ("B3", 50),
        )
    ]}]}}]}


def test_workbook_snapshot_contains_all_collected_references():
    index = workbook_evidence_index(_context())

    assert index.reference_index is not None
    assert "source!c2" in index.cause_references
    assert resolve_references(index.references, index.reference_index) == (index.references, set())


def test_agent_snapshot_excludes_failed_steps_and_other_requests():
    def step(sheet, status):
        evidence = AgentExecutionEvidence(kind=EvidenceKind.CELL, sheet_name=sheet,
            reference="B2", value=100, description="매출")
        return SimpleNamespace(status=status, result=SimpleNamespace(evidence=[evidence]))

    execution = SimpleNamespace(steps=[
        step("Source", AgentStepStatus.SUCCEEDED), step("Failed", AgentStepStatus.FAILED),
    ], failed_step_count=1, skipped_step_count=0)
    first = agent_evidence_index(execution)
    execution.steps = [step("Other", AgentStepStatus.SUCCEEDED)]
    second = agent_evidence_index(execution)
    citations = {"source!b2", "failed!b2", "other!b2"}

    assert resolve_references(citations, first.reference_index) == (
        {"source!b2"}, {"failed!b2", "other!b2"},
    )
    assert resolve_references(citations, second.reference_index) == (
        {"other!b2"}, {"source!b2", "failed!b2"},
    )


def test_fact_and_overview_validation_reuse_the_prepared_snapshot(monkeypatch):
    index = workbook_evidence_index(_context())
    calls = []

    def resolve(citations, available):
        assert available is index.reference_index
        calls.append(citations)
        return resolve_references(citations, available)

    monkeypatch.setattr(validator, "resolve_references", resolve)
    monkeypatch.setattr(workbook_overview, "resolve_references", resolve)
    insight = WorkbookInsight(title="매출", fact="매출은 100입니다.",
        category="summary", severity="info", evidence=["Source!A1:B3"], confidence=1)

    validated = validator._validate_insight(insight, index)
    assert validated is not None
    assert workbook_overview._supported(insight.fact, SimpleNamespace(insights=[validated]), index)
    assert len(calls) == 2
