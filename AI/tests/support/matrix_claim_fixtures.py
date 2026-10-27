from dataclasses import asdict
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.source_matrix_bindings import source_matrix_bindings
from tests.tabular_query_fixtures import table_fixture

MATRIX = [[None, "Latest period", "Prior period"],
          ["Revenue", 120.5, 90], ["Operating costs", 60, 55]]
QUESTION = "Planning에서 Latest period의 Revenue 값은 얼마야?"


def setup(blocks=None, sheet="Planning"):
    summary, index = table_fixture(blocks or [(10, 1, MATRIX)], sheet)
    cells = [cell.evidence() for row in index.rows for cell in row.cells]
    bindings = source_matrix_bindings(summary, index, cells)
    data = {"source_matrix_bindings": bindings}
    step = SimpleNamespace(status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
                           result=SimpleNamespace(evidence=[AgentExecutionEvidence(**asdict(cell)) for cell in cells], data=data))
    return summary, index, cells, SimpleNamespace(steps=[step])


def claim(**changes):
    return {"kind": "cell_value", "value_reference": "Planning!B11",
            "subject_reference": "Planning!B10", "property_reference": "Planning!A11",
            "period_reference": "Planning!B10", **changes}


def response(execution, claims=None, question=QUESTION, **draft_changes):
    draft = QuestionAnswerDraft(answer="An unsupported model explanation must not leak.",
                                confidence=.99, claims=claims or [claim()], **draft_changes)
    return validate_answer(question, draft, execution, False)
