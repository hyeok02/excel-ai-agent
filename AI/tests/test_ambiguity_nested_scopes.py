import asyncio
from dataclasses import replace

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.ambiguity_tables import table_candidates
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture
from tests.test_ambiguity_service import _service


def _fixture():
    first, fi = table_fixture([(1, 1, [["Record", "Amount"], ["Example", 10]])], "North")
    second, si = table_fixture([(1, 1, [["Record", "Amount"], ["Other", 20]])], "North America")
    return (replace(first, sheets=[*first.sheets, *second.sheets], sheet_count=2),
            replace(fi, rows=(*fi.rows, *si.rows)))


def test_longer_complete_sheet_name_does_not_select_its_prefix_sheet():
    summary, index = _fixture()
    assert table_candidates("North America 시트의 Amount 합계", summary, index) == []


def test_separately_named_short_and_long_sheet_names_remain_distinct():
    summary, index = _fixture()
    assert len(table_candidates("North 및 North America 시트의 Amount 합계", summary, index)) == 2


def test_sheet_name_prefix_cannot_certify_model_selected_wrong_population():
    summary, index = _fixture()
    for table in build_query_tables(summary):
        plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum")
        answer = asyncio.run(_service(QuestionIntent(False, "aggregation", (), True, plan)).answer(
            "North America 시트의 Amount 합계", summary, index,
        ))
        if table.sheet_name == "North America":
            assert answer.verification.level == "request_checked" and "20" in answer.answer
        else:
            assert answer.verification.level != "request_checked"


def test_spacing_and_unicode_source_normalization_preserves_real_source_names():
    assert mentioned_sources(["Ｎｏｒｔｈ", "North America"], "North America에서의 Amount") == {"North America"}
    assert mentioned_sources(["현황", "현황 데이터"], "현황 데이터에서의 금액") == {"현황 데이터"}
