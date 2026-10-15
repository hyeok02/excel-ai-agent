import asyncio
from io import BytesIO

from openpyxl import Workbook

from app.agent import create_default_tool_registry
from app.agent.query.index import build_workbook_data_index
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.question_formula_sources import prepare_formula_sources
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.services.workbook_parser import parse_workbook


def source_fixture(rows, formats=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    for row in rows:
        sheet.append(row)
    for address, style in (formats or {}).items():
        sheet[address].number_format = style
    output = BytesIO()
    workbook.save(output)
    content = output.getvalue()
    return parse_workbook("unfamiliar.xlsx", content), build_workbook_data_index("unfamiliar.xlsx", content)


class NoGeneratedAnswer:
    async def generate(self, *args):
        raise AssertionError("A deterministic formula answer must not invent fallback prose")


class FixedIntent:
    def __init__(self, intent):
        self.intent = intent

    async def classify(self, *args):
        return self.intent


def answer(question, summary, index, plan=None):
    kind = "aggregation" if plan and plan.operation == "numeric_summary" else "cell_lookup"
    classifier = FixedIntent(QuestionIntent(False, kind, from_model=True, tabular_query=plan))
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(), classifier=classifier)
    return asyncio.run(service.answer(question, summary, index))


def test_ephemeral_recovery_does_not_mutate_original_summary_or_index():
    summary, index = source_fixture([["Record ID", "Amount", "Input"], ["R001", "=C2*2", 12]])
    before = repr(summary), repr(index)
    sources = prepare_formula_sources(summary, index)
    assert sources.original_index is index
    assert next(cell for row in sources.index.rows for cell in row.cells if cell.address == "B2").value == 24
    assert (repr(summary), repr(index)) == before
    assert any(row.values.get("B") == 24 for table in build_query_tables(sources.summary) for row in table.rows)
    assert prepare_formula_sources(None, index).summary is None


def test_direct_recalculated_percentage_keeps_display_format_and_input_evidence():
    summary, index = source_fixture([["Input", "Rate"], [50, "=A2/100"]], {"B2": "0%"})
    result = answer("Data!B2의 값은 얼마야?", summary, index)
    assert "50%" in result.answer
    assert result.status == "limited" and result.verification.level == "source_checked"
    assert {item.reference for item in result.evidence} >= {"A2", "B2"}
    assert any("저장된 원본 계산 결과가 아닙니다" in item.description for item in result.evidence)


def test_tabular_sum_and_lookup_use_recovered_values_but_never_green_badge():
    summary, index = source_fixture([["Record ID", "Amount", "Input"],
                                     ["R001", "=C2*2", 12], ["R002", "=C3*2", 8]])
    table = build_query_tables(summary)[0]
    total = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum")
    result = answer("Amount 합계", summary, index, total)
    assert "합계 40" in result.answer
    assert result.status == "limited" and result.verification.level == "source_checked"
    assert {item.reference for item in result.evidence} >= {"B2", "B3", "C2", "C3"}
    assert all("원본 열" not in item.description for item in result.evidence if item.reference.startswith("B"))
    lookup = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["B"],
                             filters=[TabularFilter(column_id="A", operator="equals", value="R001")])
    result = answer("R001의 Amount", summary, index, lookup)
    assert "24" in result.answer and result.verification.level == "source_checked"


def test_uncached_external_formula_cannot_be_counted_as_zero_or_partial_total():
    summary, index = source_fixture([["Record ID", "Amount"], ["R001", "=IFERROR(_xll.RemoteValue(),0)"], ["R002", 8]])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum")
    result = answer("Amount 합계", summary, index, plan)
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"
    assert "Data!B2" in result.answer and "새로 고친" in result.answer
    assert "합계 8" not in result.answer and "합계 0" not in result.answer
    assert result.evidence[0].formula == "=IFERROR(_xll.RemoteValue(),0)"


def test_unrelated_missing_formula_does_not_block_known_requested_value():
    summary, index = source_fixture([["Record ID", "Amount", "External"], ["R001", 42, "=_xll.RemoteValue()"]])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["B"],
                           filters=[TabularFilter(column_id="A", operator="equals", value="R001")])
    result = answer("R001의 Amount", summary, index, plan)
    assert "42" in result.answer and result.status == "answered"
    assert result.verification.level == "request_checked"
