"""Source-independent regressions for ordinary count wording and polarity."""
import pytest

from app.agent.query.boolean_source_answers import boolean_source_answer
from app.agent.query.source_count_answers import source_count_answer
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("ending", ["행은 몇 건이야?", "레코드는 몇 개인가요?", "몇 행입니까?"])
def test_boolean_output_ending_retains_both_branches(ending):
    summary,index=table_fixture([(1,1,[["Zone","Score"],["East",0],["West",4],["North",5]])])
    response=boolean_source_answer("Zone이 East 또는 West인 " + ending,summary,index)
    assert response.status == "answered" and "2건" in response.answer
    assert response.verification.level == "request_checked"


@pytest.mark.parametrize("wording", ["값이 기록된", "값이 입력된", "값이 존재하는", "값이 있는"])
def test_present_values_count_zero_not_missing(wording):
    summary,index=table_fixture([(1,1,[["ID","Score"],["a",0],["b",4],["c",None]])])
    response=source_count_answer(f"Score {wording} 데이터는 몇 건이야?",summary,index)
    assert response is not None and response.status == "answered"
    assert "2건" in response.answer and response.verification.level == "request_checked"
    table=build_query_tables(summary)[0]
    wrong=TabularQueryPlan(operation="row_count",table_id=table.id,
                          filters=[TabularFilter(column_id="B",operator="is_blank")])
    assert execute_tabular_query(wrong,summary,index,f"Score {wording} 데이터는 몇 건이야?") is None


@pytest.mark.parametrize("tail", ["중 East 지역만", "2024년", "그리고 승인된 것만", "중 3 이상인"])
def test_presence_count_never_ignores_other_conditions(tail):
    summary,index=table_fixture([(1,1,[["ID","Score"],["a",0],["b",4],["c",None]])])
    assert source_count_answer(f"Score 값이 기록된 데이터 {tail} 몇 건이야?",summary,index) is None


@pytest.mark.parametrize("record", ["행은", "항목을", "레코드는"])
def test_rollup_keeps_explicit_total_exclusion(record):
    summary,index=table_fixture([(1,1,[["지역","Amount"],["전체",30],["동부",10],["서부",20]])])
    table=build_query_tables(summary)[0]
    question=f"전체 {record} 제외하고 지역별 Amount를 모두 더해줘"
    plan=TabularQueryPlan(operation="numeric_summary",table_id=table.id,column_ids=["B"],
                         statistic="sum",filters=[TabularFilter(column_id="A",operator="not_equals",value="전체")])
    result=execute_tabular_query(plan,summary,index,question)
    assert result is not None and result.status == "answered" and "30" in result.answer
    assert result.verification.level == "request_checked"
    assert execute_tabular_query(plan.model_copy(update={"filters":[]}),summary,index,question) is None
    assert execute_tabular_query(plan.model_copy(update={"group_by":["A"]}),summary,index,question) is None


@pytest.mark.parametrize("question", ["지역별 Amount 평균을 모두 더해줘", "지역별 Amount 비율을 모두 더해줘",
                                    "Unknown별 Amount를 모두 더해줘"])
def test_rollup_does_not_discard_derived_or_unknown_grouping(question):
    summary,index=table_fixture([(1,1,[["지역","Amount"],["동부",10],["서부",20]])])
    table=build_query_tables(summary)[0]
    plan=TabularQueryPlan(operation="numeric_summary",table_id=table.id,column_ids=["B"],statistic="sum")
    assert execute_tabular_query(plan,summary,index,question) is None


def test_short_header_cannot_match_inside_a_total_row_label():
    from app.agent.query.tabular_request_literals import source_headers
    summary,index=table_fixture([(1,1,[["분류","계"],["총합계",30],["동부",10],["서부",20]])])
    table=build_query_tables(summary)[0]
    question="총합계 행은 제외하고 분류별 계를 모두 더해줘"
    assert [(column,match.group()) for column,match in source_headers(question,table)] == [("A","분류"),("B","계")]
    plan=TabularQueryPlan(operation="numeric_summary",table_id=table.id,column_ids=["B"],statistic="sum",
        filters=[TabularFilter(column_id="A",operator="not_equals",value="총합계")])
    result=execute_tabular_query(plan,summary,index,question)
    assert result is not None and result.verification.level == "request_checked" and "30" in result.answer


@pytest.mark.parametrize("tail", ["두 배로 알려줘", "절반으로 알려줘", "10을 빼줘", "5 더해줘",
                                 "10%로 계산해줘", "USD로 환산해줘", "비율로 알려줘"])
def test_rollup_cannot_certify_a_raw_sum_when_postprocessing_was_requested(tail):
    summary,index=table_fixture([(1,1,[["지역","Amount"],["전체",30],["동부",10],["서부",20]])])
    table=build_query_tables(summary)[0]
    plan=TabularQueryPlan(operation="numeric_summary",table_id=table.id,column_ids=["B"],statistic="sum",
        filters=[TabularFilter(column_id="A",operator="not_equals",value="전체")])
    assert execute_tabular_query(plan,summary,index,"전체 행은 제외하고 지역별 Amount를 모두 더해 " + tail) is None


@pytest.mark.parametrize("expression", ["합계를 두 배로 해서", "합계의 절반을", "두배를", "제곱을",
                                       "합계에 10을 더해서", "* 2를", "합계 / 2를"])
def test_rollup_cannot_ignore_derived_operations_before_the_sum_phrase(expression):
    summary,index=table_fixture([(1,1,[["지역","Amount"],["전체",30],["동부",10],["서부",20]])])
    table=build_query_tables(summary)[0]
    plan=TabularQueryPlan(operation="numeric_summary",table_id=table.id,column_ids=["B"],statistic="sum",
        filters=[TabularFilter(column_id="A",operator="not_equals",value="전체")])
    question="전체 행은 제외하고 지역별 Amount " + expression + " 모두 더해줘"
    assert execute_tabular_query(plan,summary,index,question) is None
