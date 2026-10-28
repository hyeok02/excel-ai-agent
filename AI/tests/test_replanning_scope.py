"""Recovery must distinguish join instructions from source words locally."""
from dataclasses import replace

import pytest

from app.agent.query.replanning_scope import single_table_recovery_allowed
from tests.tabular_query_fixtures import table_fixture


@pytest.fixture(params=[(2, 1), (8, 4)])
def summary(request):
    row, column = request.param
    result, _ = table_fixture([(row, column, [
        ["Account", "Status", "Join Count", "결합구분", "Amount"],
        ["Orion", "join", 4, "병합 완료", 17],
        ["Maple", "open", 3, "단독", 31],
        ["Join Team", "match", 2, "조인 대상", 7],
    ])], sheet_name="Join Records")
    return result


@pytest.mark.parametrize("question", [
    "고객 표와 연결해서 Orion의 Amount 알려줘",
    "Join with customer data and show Amount for Orion",
    "Merge customer data with orders and show Amount",
    "두 표를 결합한 Amount 합계",
    "고객 표와 주문 표를 병합해 Amount 합계",
    "고객 표와 매칭해서 Amount 알려줘",
    "Combine orders and customers and show Amount",
    "Join Records with customer data and show Amount",
    "'없는 join 명령'을 실행해줘",
])
def test_cross_table_request_cannot_be_recovered_as_single_table(summary, question):
    assert not single_table_recovery_allowed(question, summary)


@pytest.mark.parametrize("question", [
    "Orion의 Amount 합계 알려줘", "Join Count 합계 알려줘",
    "Sum of Join Count", "결합구분별 Amount 합계",
    "Status가 join인 Amount 합계", "Status is join",
    "Status가 'join'인 Amount 합계",
    "결합구분이 ‘병합 완료’인 Amount 합계",
    "결합구분이 조인 대상인 Amount 합계",
    "Join Team의 Amount 알려줘", "Join Records 시트 Amount 합계",
    "Join Records에서 Amount 합계", "in sheet Join Records show Amount",
    "'Join Records' 시트의 'Join Count' 합계",
])
def test_actual_source_names_and_values_do_not_disable_normal_recovery(summary, question):
    assert single_table_recovery_allowed(question, summary)


@pytest.mark.parametrize("question", [
    "Status가 'join'인 고객을 다른 표와 연결해서 Amount 합계",
    "Status is join; join customers with orders and show Amount",
    "Join Records 시트와 고객 표를 조인해서 Amount 합계",
    "Join Count 합계를 구하려고 고객 표와 결합해줘",
    "Show Join Count and join customer data with orders",
    "결합구분이 병합 완료인 자료를 다른 표와 병합해 Amount 합계",
    "Join Team의 Amount를 고객 표와 연결해서 알려줘",
])
def test_source_join_word_does_not_hide_separate_join_instruction(summary, question):
    assert not single_table_recovery_allowed(question, summary)


def test_source_phrase_is_not_a_global_instruction_mask():
    summary, _ = table_fixture([(3, 2, [
        ["Account", "Amount"], ["Join customers", 17], ["Elsewhere", 31],
    ])], sheet_name="Arbitrary")
    assert single_table_recovery_allowed("'Join customers'의 Amount 알려줘", summary)
    assert not single_table_recovery_allowed("Join customers with orders and show Amount", summary)


@pytest.mark.parametrize("question", [
    "combined total of Amount from both tables",
    "combined sum of Amount across two sheets",
    "combined total of Amount from customer and order tables",
    "combine customer and order tables and show the total of Amount",
    "combined total of Amount from 두 표",
    "combined total of Amount; join Customers with Orders",
])
def test_combined_total_cannot_hide_explicit_multiple_sources(summary, question):
    assert not single_table_recovery_allowed(question, summary)


def test_combined_total_cannot_hide_two_named_source_sheets():
    first, _ = table_fixture([(3, 2, [["Account", "Amount"], ["Orion", 17], ["Other", 31]])],
                             sheet_name="Customers")
    second, _ = table_fixture([(7, 4, [["Account", "Amount"], ["Orion", 90], ["Other", 4]])],
                              sheet_name="Orders")
    both = replace(first, sheet_count=2, sheets=[*first.sheets, *second.sheets])
    assert single_table_recovery_allowed("combined total of Amount from Customers", both)
    assert not single_table_recovery_allowed("combined total of Amount from Customers and Orders", both)
