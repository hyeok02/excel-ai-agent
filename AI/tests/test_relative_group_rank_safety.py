"""Source literal collisions and absent populations cannot establish a rank anchor."""
import pytest

from tests.support.advanced_qna_fixtures import checked, group_plan, source
from tests.support.large_workbook_fixtures import ask, assert_not_certified, offline, tiny_caps
from tests.test_relative_group_ranking import plan, question


@pytest.mark.parametrize("label", ["After Tax Profit", "다음달 판매량", "Next Rank"])
def test_relative_words_in_source_headers_do_not_block_normal_rank(label):
    summary, index, _ = source([["Record", label, "Department"], ["a", 10, "Alpha"], ["b", 20, "Beta"]])
    text = f"Records 시트 Department별 {label} 합계 상위 1개"
    answer = ask(text, summary, index, group_plan(summary, order_by="B", limit=1))
    checked(answer, scan=False)
    assert 'Department: "Beta"' in answer.answer


@pytest.mark.parametrize("label", ["After Tax Profit", "다음달 판매량", "Next Rank"])
def test_relative_words_in_headers_do_not_block_real_anchor(label):
    summary, index, _ = source([["Record", label, "Department"], ["a", 30, "Alpha"],
                              ["b", 20, "Beta"], ["c", 10, "Gamma"]])
    text = f"Records 시트 Department별 {label} 합계 내림차순에서 Beta 다음 순위"
    answer = ask(text, summary, index, plan(summary))
    checked(answer, scan=False)
    assert 'Department: "Gamma"' in answer.answer


@pytest.mark.parametrize("anchor", ["Beta", "beta", " Beta "])
@pytest.mark.parametrize("streamed", [False, True])
def test_case_and_spacing_collisions_across_full_source_never_guess_anchor(anchor, streamed, request):
    if streamed:
        request.getfixturevalue("tiny_caps")
    matrix = [["Record", "Amount", "Department"], ["a", 100, "Alpha"], ["b", 70, "Beta"],
              ["c", 60, "Gamma"], ["d", 50, "beta"], ["e", 40, " Beta "], ["f", 30, "Last"]]
    summary, index, _ = source(matrix)
    assert_not_certified(ask(question(), summary, index, plan(summary, anchor)))


@pytest.mark.parametrize("anchor", ["Beta", "beta", " Beta "])
def test_unique_case_spacing_variant_resolves_to_one_actual_source_group(anchor):
    summary, index, _ = source([["Record", "Amount", "Department"], ["a", 100, "Alpha"],
                              ["b", 70, "Beta"], ["c", 60, "Gamma"]])
    answer = ask(question(), summary, index, plan(summary, anchor))
    checked(answer, scan=False)
    assert 'Department: "Gamma"' in answer.answer and '기준 항목 "Beta"' in answer.answer


@pytest.mark.parametrize("typed,literal", [(True, "True"), (1, "1")])
@pytest.mark.parametrize("use_text", [False, True])
def test_same_spelling_different_identity_types_cannot_select_different_ranks(typed, literal, use_text, tiny_caps):
    summary, index, _ = source([["Record", "Amount", "Department"], ["a", 100, "Alpha"],
        ["b", 70, typed], ["c", 60, "Gamma"], ["d", 50, literal], ["e", 40, "Last"]])
    anchor = literal if use_text else typed
    assert_not_certified(ask(question(literal), summary, index, plan(summary, anchor)))


def test_relative_answer_leads_with_winner_and_metric_not_technical_scope():
    summary, index, _ = source([["Record", "Amount", "Department"], ["a", 100, "Alpha"],
                              ["b", 70, "Beta"], ["c", 60, "Gamma"]])
    answer = ask(question(), summary, index, plan(summary))
    assert answer.answer.startswith("Beta 다음 순위는 Gamma이며, Amount 합계는 60입니다.")
    assert "3개 행" in answer.answer and "Department별 집계" in answer.answer


def test_relative_tie_lead_names_every_joint_winner_and_shared_value(tiny_caps):
    summary, index, _ = source([["Record", "Amount", "Department"], ["a", 100, "Alpha"],
                              ["b", 70, "Beta"], ["c", 60, "Gamma"], ["d", 60, "Other"]])
    answer = ask(question(), summary, index, plan(summary))
    assert answer.answer.startswith("Beta 다음 순위는 Gamma, Other이며, Amount 합계는 각각 60입니다 (공동 순위).")


def test_relative_no_successor_lead_is_explicit_absence():
    summary, index, _ = source([["Record", "Amount", "Department"], ["a", 100, "Alpha"], ["b", 70, "Beta"]])
    answer = ask(question(), summary, index, plan(summary))
    assert answer.answer.startswith("Beta 다음 순위의 그룹은 없습니다.")
