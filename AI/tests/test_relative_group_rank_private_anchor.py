"""Trusted request labels survive binding without entering the model/public schema."""
import pytest
from pydantic import ValidationError

from app.agent.query.grouped_tabular_results import GroupedAccumulator
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import RelativeGroupRank, TabularQueryPlan
from tests.test_relative_group_ranking import plan
from tests.support.advanced_qna_fixtures import source
from tests.support.large_workbook_fixtures import ask, assert_not_certified, offline, tiny_caps


def fixture():
    return source([["Record", "Amount", "Department"], ["a", 100, "Cookies"],
        ["b", 80, "Bars"], ["c", 60, "Other"], ["d", 50, "쿠키"]])


def test_original_request_label_is_not_model_controllable_or_serialized():
    anchor = RelativeGroupRank(column_id="C", value="Cookies")
    anchor._original_request_label = "쿠키"
    assert "_original_request_label" not in anchor.model_dump()
    assert "_original_request_label" not in RelativeGroupRank.model_json_schema()["properties"]
    assert "_original_request_label" not in str(TabularQueryPlan.model_json_schema())
    with pytest.raises(ValidationError):
        RelativeGroupRank.model_validate({"column_id": "C", "value": "Cookies", "_original_request_label": "쿠키"})


def test_private_original_label_survives_plan_and_column_binding_copies():
    summary, _, _ = fixture()
    selected = plan(summary, "Cookies")
    selected.relative_rank._original_request_label = "쿠키"
    copied = selected.model_copy(update={"limit": 1})
    bound = bind_tabular_plan(copied, build_query_tables(summary)[0])
    assert bound.relative_rank._original_request_label == "쿠키"


def test_full_accumulator_rejects_late_original_label_behind_an_alias():
    summary, _, _ = fixture()
    table = build_query_tables(summary)[0]
    selected = plan(summary, "Cookies")
    selected.relative_rank._original_request_label = "쿠키"
    result = GroupedAccumulator(selected, table)
    for row in table.rows:
        assert result.add(row)
    assert result.render()[0] is None


def test_streamed_original_label_at_tail_cannot_be_overruled_by_model_translation(tiny_caps):
    summary, index, _ = fixture()
    selected = plan(summary, "Cookies")
    selected.relative_rank._original_request_label = "쿠키"
    text = "Records 시트 Department별 Amount 합계 내림차순에서 Cookies 다음 순위"
    assert_not_certified(ask(text, summary, index, selected))


def test_exact_original_anchor_is_not_rejected_by_private_metadata():
    summary, _, _ = fixture()
    table = build_query_tables(summary)[0]
    selected = plan(summary, "쿠키", "before")
    selected.relative_rank._original_request_label = "쿠키"
    result = GroupedAccumulator(selected, table)
    for row in table.rows:
        assert result.add(row)
    assert result.render()[0].startswith("쿠키 이전 순위는 Other")
