"""Formula recovery restrictions belong to the affected part before synthesis."""
import asyncio
from types import SimpleNamespace

from app.agent.query.composite_execution import composite_answer
from app.agent.query.composite_models import CompositeQuestionPart, CompositeQueryPlan
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.query.intent_models import QuestionIntent
from tests.test_composite_execution import answer
from tests.support.large_workbook_fixtures import offline


def test_recalculated_formula_marks_part_limited_and_prevents_global_green():
    cells = (IndexedCell("Records", "A2", 5, None), IndexedCell("Records", "B2", None, "=A2*2"))
    original = WorkbookDataIndex("source.xlsx", (IndexedRow("Records", 2, cells),), 2, False)
    sources = SimpleNamespace(original_index=original, resolutions={"Records!B2": SimpleNamespace(
        reference="Records!B2", status="recovered", value=10, inputs=("Records!A2",))})
    intent = QuestionIntent(False, composite_query=CompositeQueryPlan(parts=[
        CompositeQuestionPart(source_text="Amount 합계"), CompositeQuestionPart(source_text="Customer 수")]))

    async def callback(question, current, **options):
        result = answer(question)
        if question == "Customer 수":
            result.evidence[0].reference = "C2"
        return result

    result = asyncio.run(composite_answer("Amount 합계; Customer 수", sources, intent, callback))
    assert result.status == "limited" and result.verification.level == "source_checked"
    assert any("문항 1" in note and "재계산" in note for note in result.limitations)
    assert not any("문항 2" in note and "재계산" in note for note in result.limitations)
    assert any("재계산" in item.label for item in result.evidence)
    assert "compound_parts_2" not in result.verification.checks
