"""Regression for unrelated glossary cells being reported as verified headcount."""
from app.agent.contracts import AgentToolContext
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.query.intent_models import QuestionIntent
from app.agent.tools.workbook_cell_lookups import build_cell_lookup
from app.agent.tools.workbook_data import WorkbookDataSearchTool
from app.agent.tools.workbook_headers import build_header_context
from app.services.workbook_parsing.models import WorkbookSummary


def _row(number, values):
    return IndexedRow("Data", number, tuple(
        IndexedCell("Data", f"{column}{number}", value, None)
        for column, value in values.items()
    ))


def _lookup(rows, question):
    return build_cell_lookup(rows, build_header_context(tuple(rows), rows), question)


def test_classifier_cannot_replace_a_missing_equipment_id():
    rows = (
        _row(1, {"A": "설비코드", "B": "측정값"}),
        _row(2, {"A": "EX-101", "B": 3.2}),
        _row(3, {"A": "EX-102", "B": 68.4}),
    )
    question = "EX-999의 측정값은?"
    context = AgentToolContext(
        WorkbookSummary("equipment.xlsx", 0, []),
        WorkbookDataIndex("equipment.xlsx", rows, 6, False), question,
        QuestionIntent(False, "cell_lookup", ("EX-102",), True),
    )

    result = WorkbookDataSearchTool().execute(context, {"query": question})

    assert result.data["cell_lookup"] is None


def test_comparison_question_is_not_answered_with_a_single_existing_cell():
    rows = [
        _row(1, {"A": "설비코드", "B": "측정값"}),
        _row(2, {"A": "EX-102", "B": 68.4}),
    ]

    assert _lookup(rows, "EX-102 측정값 변화를 비교해줘") is None
    assert _lookup(rows, "EX-102 측정값은?")["value"] == 68.4


def test_shared_total_word_cannot_change_employees_into_debt():
    rows = [
        _row(1, {"A": "Company", "B": "Total Debt"}),
        _row(2, {"A": "Acme", "B": 500}),
    ]

    assert _lookup(rows, "Acme Total Employees value") is None
    assert _lookup(rows, "Acme Total Debt value")["value"] == 500


def test_header_from_later_rows_cannot_describe_an_earlier_glossary_entry():
    rows = [
        _row(13, {"B": "Topic Tags", "C": "Business operations"}),
        _row(22, {"B": "Total Debt", "C": "Description"}),
        _row(23, {"B": 100, "C": "Company one"}),
        _row(24, {"B": 200, "C": "Company two"}),
    ]

    assert _lookup(rows, "Business operations Total Debt value") is None


def test_zero_is_a_valid_cell_value():
    rows = [
        _row(1, {"A": "설비코드", "B": "측정값"}),
        _row(2, {"A": "EX-102", "B": 0}),
    ]

    assert _lookup(rows, "EX-102 측정값은?")["value"] == 0
