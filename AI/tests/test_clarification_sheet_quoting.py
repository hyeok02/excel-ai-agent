import asyncio

from openpyxl.utils.cell import quote_sheetname
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_scope import explicit_ranges
from tests.support.clarification_fixtures import fixture, initial, QueryClassifier, selection, service
from tests.test_clarification_conversation import selected_history


@pytest.mark.parametrize("sheet_name", ["O'Brien", "팀의 '원본'", "Data!Sales"])
def test_selected_table_with_quoted_sheet_name_survives_followup(sheet_name):
    summary, index = fixture(sheet_name)
    answer = initial(summary, index)
    option = answer.clarification_options[1]
    assert option.question.startswith(quote_sheetname(sheet_name) + "!A1:C3")
    assert explicit_ranges(option.question) == [(sheet_name, "A1:C3")]
    classifier = QueryClassifier(build_query_tables(summary)[0], "C")
    chosen = asyncio.run(service(classifier).answer(option.question, summary, index, selection(answer, option)))
    assert chosen.status == "answered" and "합계 300" in chosen.answer
    assert chosen.verification.level == "request_checked"
    average = QueryClassifier(build_query_tables(summary)[0], "C", "average")
    followup = asyncio.run(service(average).answer(
        "그 항목 평균은?", summary, index, selected_history(summary, index),
    ))
    assert "평균 150" in followup.answer
    assert followup.resolved_question.startswith(quote_sheetname(sheet_name) + "!A1:C3")
    assert followup.verification.level == "source_checked"


def test_distinct_apostrophe_sheet_names_cannot_bind_to_each_other():
    assert explicit_ranges("'O''Brien'!$A$1:$C$3") == [("O'Brien", "A$1:C$3")]
    assert explicit_ranges("'O''''Brien'!A1:C3") == [("O''Brien", "A1:C3")]
