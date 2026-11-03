"""Relative ranks use a verified source anchor, never exclusion plus global top one."""
import pytest

from app.agent.query.grouped_tabular_results import GroupedAccumulator
from app.agent.query.tabular_feature_contract import feature_contract_matches
from tests.support.advanced_qna_fixtures import checked, group_plan, source
from tests.support.large_workbook_fixtures import ask, assert_not_certified, offline, tiny_caps
from app.agent.query.tabular_catalog import build_query_tables


def fixture(rows=None):
    return source(rows or [["Record", "Amount", "Department"], ["a", 80, "Alpha"],
                          ["b", 30, "Beta"], ["c", 60, "Gamma"], ["d", 40, "Beta"]])


def plan(summary, anchor="Beta", direction="after", **changes):
    return group_plan(summary, order_by="B", limit=1,
                      relative_rank={"column_id": "C", "value": anchor, "direction": direction}, **changes)


def question(anchor="Beta", direction="after", descending=True):
    return ("Records 시트 Department별 Amount 합계 " + ("내림차순" if descending else "오름차순")
            + f"에서 {anchor} " + ("다음" if direction == "after" else "이전") + " 순위")


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("direction,descending,winner", [("after", True, "Gamma"),
    ("before", True, "Alpha"), ("after", False, "Alpha"), ("before", False, "Gamma")])
def test_adjacent_complete_group_rank_not_anchor_exclusion(streamed, direction, descending, winner, request):
    if streamed:
        request.getfixturevalue("tiny_caps")
    summary, index, _ = fixture()
    answer = ask(question(direction=direction, descending=descending), summary, index,
                 plan(summary, direction=direction, descending=descending))
    checked(answer, scan=streamed)
    assert f'Department: "{winner}"' in answer.answer and "기준 항목" in answer.answer
    assert 'Department: "Beta"' not in answer.answer
    assert "relative_group_rank" in answer.verification.checks


def test_ties_skip_anchor_peers_and_return_every_adjacent_rank(tiny_caps):
    summary, index, _ = fixture([["Record", "Amount", "Department"], ["a", 100, "Alpha"],
        ["b", 100, "Peer"], ["c", 70, "Beta"], ["d", 70, "Gamma"], ["e", 1, "Last"]])
    answer = ask(question("Alpha"), summary, index, plan(summary, "Alpha"))
    checked(answer, scan=True)
    assert all(f'Department: "{name}"' in answer.answer for name in ["Beta", "Gamma"])
    assert all(f'Department: "{name}"' not in answer.answer for name in ["Alpha", "Peer", "Last"])
    assert answer.status == "limited" and len(answer.limitations) == 2


def test_last_rank_returns_explicit_absence_not_global_winner():
    summary, index, _ = fixture()
    answer = ask(question("Gamma"), summary, index, plan(summary, "Gamma"))
    checked(answer, scan=False)
    assert "순위의 그룹은 없습니다" in answer.answer and 'Department: "Alpha"' not in answer.answer


@pytest.mark.parametrize("wrong", ["anchor", "direction", "metric", "group", "omitted", "extra_filter"])
def test_unrelated_or_missing_anchor_contract_cannot_get_verified_badge(wrong):
    summary, index, _ = fixture()
    selected = plan(summary)
    updates = {"anchor": {"relative_rank": selected.relative_rank.model_copy(update={"value": "Alpha"})},
        "direction": {"relative_rank": selected.relative_rank.model_copy(update={"direction": "before"})},
        "metric": {"column_ids": ["A"], "order_by": "A"}, "group": {"group_by": ["A"]},
        "omitted": {"relative_rank": None},
        "extra_filter": {"filters": [{"column_id": "C", "operator": "not_equals", "value": "Beta"}]}}
    selected = type(selected).model_validate(selected.model_dump() | updates[wrong])
    answer = ask(question(), summary, index, selected)
    assert_not_certified(answer)


def test_missing_source_anchor_never_returns_a_position_guess(tiny_caps):
    summary, index, _ = fixture()
    answer = ask(question("Missing"), summary, index, plan(summary, "Missing"))
    assert_not_certified(answer)


def test_excessive_ties_discard_the_entire_answer(monkeypatch):
    monkeypatch.setattr("app.agent.query.relative_group_ranking.MAX_RELATIVE_TIES", 1)
    summary, index, _ = fixture([["Record", "Amount", "Department"], ["a", 100, "Alpha"],
                              ["b", 50, "Beta"], ["c", 50, "Gamma"]])
    assert_not_certified(ask(question("Alpha"), summary, index, plan(summary, "Alpha")))


def test_relative_alias_is_not_accepted_as_exact_source_identity():
    summary, index, _ = fixture()
    assert_not_certified(ask(question("베타"), summary, index, plan(summary, "Beta")))


def test_anchor_cannot_belong_to_another_explicit_field():
    summary, index, _ = fixture()
    text = "Records 시트 Department별 Amount 합계 내림차순에서 Record Beta 다음 순위"
    assert_not_certified(ask(text, summary, index, plan(summary)))


def test_relative_rank_cannot_silently_reduce_two_requested_next_groups_to_one():
    summary, index, _ = fixture()
    text = question() + " 상위 2개"
    assert_not_certified(ask(text, summary, index, plan(summary)))


def test_english_relative_phrase_uses_the_same_anchored_population():
    summary, index, _ = fixture()
    text = "Records 시트 Department별 Amount 합계 내림차순에서 after Beta"
    answer = ask(text, summary, index, plan(summary))
    checked(answer, scan=False)
    assert 'Department: "Gamma"' in answer.answer


def test_unknown_tail_measure_invalidates_relative_rank(tiny_caps):
    summary, index, _ = fixture([["Record", "Amount", "Department"], ["a", 100, "Alpha"],
        ["b", 70, "Beta"], ["c", 50, "Gamma"], ["d", "=UNKNOWN()", "Beta"]])
    assert_not_certified(ask(question(), summary, index, plan(summary)))


@pytest.mark.parametrize("streamed", [False, True])
def test_empty_filtered_population_cannot_prove_the_relative_anchor(streamed, request):
    if streamed:
        request.getfixturevalue("tiny_caps")
    summary, index, _ = fixture()
    selected = plan(summary, filters=[{"column_id": "A", "operator": "equals", "value": "missing"}])
    text = "Records 시트 Record가 missing인 Department별 Amount 합계 내림차순에서 Beta 다음 순위"
    answer = ask(text, summary, index, selected)
    assert_not_certified(answer)
    assert "relative_group_rank" not in answer.verification.checks


def test_empty_reducer_cannot_report_verified_relative_absence():
    summary, _, _ = fixture()
    table = build_query_tables(summary)[0]
    assert GroupedAccumulator(plan(summary), table).render()[0] is None


@pytest.mark.parametrize("field,value", [("share_of_total", True), ("per_group_limit", 1),
    ("limit", 2), ("having", [{"column_id": "B", "operator": "greater_than", "value": 1}])])
def test_unsupported_combinations_fail_closed(field, value):
    summary, _, _ = fixture()
    selected = plan(summary)
    selected = type(selected).model_validate(selected.model_dump() | {field: value})
    table = build_query_tables(summary)[0]
    assert not feature_contract_matches(selected, table)
    assert GroupedAccumulator(selected, table).render()[0] is None
