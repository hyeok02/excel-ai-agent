"""Follow-up hints must retain the cited field, not just the first columns."""
import asyncio
from dataclasses import replace

import pytest
from openpyxl.utils import get_column_letter

from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.conversation_sources import source_bound_context
from app.agent.query.tabular_catalog import build_query_tables
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("sheet,width,start_column", [
    ("Warehouse", 20, 1), ("별도 보고", 32, 4), ("O'Brien Metrics", 80, 2),
])
def test_value_only_citation_keeps_its_header_in_a_wide_moved_table(sheet, width, start_column):
    headers = ["Record", *[f"Measure {i}" for i in range(1, width)]]
    summary, index = table_fixture([(7, start_column, [headers, ["Unit-X", *range(1, width)]])], sheet)
    column = get_column_letter(start_column + width - 1)
    quoted = sheet.replace("'", "''")
    context = QuestionConversation(turns=[{
        "question": f"Unit-X의 Measure {width - 1} 값은?",
        "evidence": [f"'{quoted}'!{column}8"],
    }])
    entries = source_bound_context(context, summary, index)
    values = {cell["reference"]: cell["value"] for cell in entries[0]["source_cells"]}
    assert values[f"{sheet}!{column}7"] == headers[-1]
    assert values[f"{sheet}!{column}8"] == width - 1
    assert "Unit-X" in values.values()
    assert len(values) <= 24


def test_same_name_tables_keep_the_cited_sections_source_caption(monkeypatch):
    summary, index = table_fixture([
        (1, 1, [["North division", "USD"]]),
        (3, 1, [["Record", "Revenue"], ["Unit-X", 12]]),
        (7, 1, [["South division", "EUR"]]),
        (9, 1, [["Record", "Revenue"], ["Unit-X", 48]]),
    ], "Report")
    tables = build_query_tables(summary)
    monkeypatch.setattr("app.agent.query.conversation_sources.build_query_tables", lambda _: [
        replace(table, context=(("Report!A1", "North division"), ("Report!B1", "USD")))
        if table.reference == "A3:B4" else
        replace(table, context=(("Report!A7", "South division"), ("Report!B7", "EUR")))
        for table in tables
    ])
    context = QuestionConversation(turns=[{
        "question": "North division의 Revenue는?", "evidence": ["Report!B4"],
    }])
    entries = source_bound_context(context, summary, index)
    values = {cell["reference"]: cell["value"] for cell in entries[0]["source_cells"]}
    assert values["Report!A1"] == "North division"
    assert values["Report!B1"] == "USD"
    assert "Report!A7" not in values and "Report!B7" not in values


def test_source_number_format_survives_context_without_copying_answer_prose():
    summary, index = table_fixture([(1, 1, [["Record", "Ratio"], ["Unit-X", .25]])], "Ratios")
    index = replace(index, rows=tuple(replace(row, cells=tuple(
        replace(cell, number_format="0.0%") if cell.address == "B2" else cell for cell in row.cells
    )) for row in index.rows))
    context = QuestionConversation(turns=[{"question": "Unit-X의 Ratio?", "evidence": ["Ratios!B2"]}])
    entry = source_bound_context(context, summary, index)[0]
    cell = next(cell for cell in entry["source_cells"] if cell["reference"] == "Ratios!B2")
    assert cell["value"] == .25 and cell["number_format"] == "0.0%"
    assert "answer" not in entry["hint"]


def test_far_right_followup_reaches_verified_calculation_without_claiming_intent_proof():
    from app.agent import create_default_tool_registry
    from app.agent.query.conversation_models import ContextResolutionDraft
    from app.agent.query.intent_models import QuestionIntent
    from app.agent.query.service import WorkbookQuestionService
    from app.agent.query.tabular_query_models import TabularQueryPlan
    from tests.test_question_formula_integration import FixedIntent, NoGeneratedAnswer

    headers = ["Record", *[f"Measure {i}" for i in range(1, 20)]]
    summary, index = table_fixture([(1, 1, [
        headers, ["Unit-X", *range(1, 19), 12], ["Unit-Y", *range(1, 19), 18],
    ])], "Metrics")
    plan = TabularQueryPlan(operation="numeric_summary", table_id="Metrics!A1:T3",
                            column_ids=["T"], statistic="sum")

    class Resolver:
        async def resolve(self, _, entries):
            values = {cell["reference"]: cell["value"] for cell in entries[0]["source_cells"]}
            assert values["Metrics!T1"] == "Measure 19"
            return ContextResolutionDraft(status="resolved", context_ids=["turn:0"],
                                          question="Metrics 시트의 Measure 19 합계를 알려줘")

    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(),
        classifier=FixedIntent(QuestionIntent(False, "aggregation", (), True, plan)),
        context_resolver=Resolver())
    context = QuestionConversation(turns=[{
        "question": "Unit-X의 Measure 19 값은?", "evidence": ["Metrics!T2"],
    }])
    answer = asyncio.run(service.answer("그 항목의 합계를 알려줘", summary, index, context))
    assert "합계 30" in answer.answer
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "context_resolved" in answer.verification.checks
    assert "request_alignment" not in answer.verification.checks
    assert answer.resolved_question == "Metrics 시트의 Measure 19 합계를 알려줘"
