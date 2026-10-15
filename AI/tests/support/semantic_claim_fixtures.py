from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.models import QuestionAnswerDraft
from app.services.provenance import EvidenceKind


def evidence(address, value, header="", sheet="Data", formula=None):
    return AgentExecutionEvidence(kind=EvidenceKind.CELL, sheet_name=sheet, reference=address,
                                  value=value, description=header, formula=formula)


def execution(cells, facts=()):
    step = SimpleNamespace(status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
                           result=SimpleNamespace(evidence=cells, data={"verified_insights": list(facts)}))
    return SimpleNamespace(steps=[step])


def answer(cells, claims, question="네트워크 안정 값은?", text="정상입니다.", facts=(), limitations=()):
    draft = QuestionAnswerDraft(answer=text, evidence=[], confidence=0.99,
                                claims=claims, limitations=list(limitations))
    return validate_answer(question, draft, execution(cells, facts), False)


def grid():
    return [evidence("A1", "장비"), evidence("B1", "네트워크 안정"), evidence("C1", "기간"),
            evidence("A2", "장비-A", "장비"), evidence("B2", "x", "네트워크 안정"),
            evidence("C2", "2024-09-01", "기간"), evidence("A3", "장비-B", "장비"),
            evidence("B3", "o", "네트워크 안정"), evidence("C3", "2025-09-01", "기간")]


def observation(**overrides):
    return {"kind": "cell_value", "value_reference": "Data!B2", "subject_reference": "Data!A2",
            "property_reference": "Data!B1", "period_reference": "Data!C2", **overrides}
