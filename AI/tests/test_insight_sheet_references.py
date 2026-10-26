from decimal import Decimal
from types import SimpleNamespace

import pytest
from openpyxl.utils.cell import quote_sheetname

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.services.insights.models import WorkbookInsight
from app.services.insights.verification.validation_index import (
    agent_evidence_index, workbook_evidence_index,
)
from app.services.insights.verification.validator import _validate_insight
from app.services.provenance import EvidenceKind


NAMES = ["Arbitrary holdings", "O'Brien", "Owner's holdings"]


def _context(name):
    return {"sheets": [{"name": name, "formula_samples": [{"cell": "C2", "formula": "=B2*2"}],
        "business_facts": {"selected_records": [{"location": "A1:B3", "values": [
            {"cell": address, "value": value} for address, value in (
                ("A1", "항목"), ("B1", "금액"), ("A2", "매출"),
                ("B2", 100), ("A3", "비용"), ("B3", 50),
            )
        ]}]}}]}


@pytest.mark.parametrize("name", NAMES)
def test_workbook_index_preserves_the_complete_sheet_name(name):
    index = workbook_evidence_index(_context(name))
    expected = f"{name.casefold()}!b2"
    assert expected in index.references
    assert Decimal("100") in index.reference_numbers[expected]
    assert f"{name.casefold()}!a1:b3" in index.references
    assert f"{name.casefold()}!c2" in index.cause_references
    assert any(expected in item.references and item.value == "100"
               for item in index.observations)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("value,valid", [(100, True), (50, False)])
def test_correct_values_survive_and_wrong_bindings_remain_blocked(name, value, valid):
    index = workbook_evidence_index(_context(name))
    insight = WorkbookInsight(
        title="매출", fact=f"매출은 {value}입니다.", category="summary", severity="info",
        evidence=[f"{quote_sheetname(name)}!A1:B3"], confidence=1,
    )
    result = _validate_insight(insight, index)
    assert (result is not None) is valid


@pytest.mark.parametrize("name", NAMES)
def test_agent_evidence_keeps_quoted_sheet_identity(name):
    evidence = AgentExecutionEvidence(kind=EvidenceKind.CELL, sheet_name=name,
        reference="B2", value=100, description="매출")
    execution = SimpleNamespace(steps=[SimpleNamespace(status=AgentStepStatus.SUCCEEDED,
        result=SimpleNamespace(evidence=[evidence]))], failed_step_count=0, skipped_step_count=0)
    index = agent_evidence_index(execution)
    assert index.references == {f"{name.casefold()}!b2"}
    assert index.reference_numbers[f"{name.casefold()}!b2"] == {Decimal("100")}
