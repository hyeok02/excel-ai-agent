"""A whole-table frequency plan answers only the column the question names."""
from datetime import datetime

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_named_scope import named_column_scope
from app.agent.query.tabular_results import _label
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture

MATRIX = [
    ["Headline", "Event Date", "Event Type", "Description"],
    ["Alpha opens plant", "2025-12-01T00:00:00", "Expansion", "long text one"],
    ["Beta pays dividend", "2025-12-09T00:00:00", "Dividend", "long text two"],
    ["Gamma at conference", "2025-12-09T00:00:00", "Conference", "long text three"],
]


def _answer(question, identity=("A",)):
    summary, index = table_fixture([(1, 1, MATRIX)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="frequencies", table_id=table.id, column_scope="all_attributes",
                            identity_column_ids=list(identity))
    return execute_tabular_query(plan, summary, index, question)


def test_a_named_column_narrows_a_whole_table_summary() -> None:
    answer = _answer("사건 발생일(Event Date) 분포를 항목별로 요약해줘")

    assert answer.answer.startswith("‘Event Date’: ‘2025-12-01’ 1건, ‘2025-12-09’ 2건")
    assert "Event Type" not in answer.answer and "long text" not in answer.answer


def test_a_longer_header_wins_over_its_prefix_and_both_named_columns_stay() -> None:
    answer = _answer("Event Type과 Description 항목별 요약")

    assert [line.split("’: ")[0] for line in answer.answer.splitlines()] == ["‘Event Type", "‘Description"]


def test_without_a_named_column_every_attribute_is_summarised() -> None:
    answer = _answer("이 표를 항목별로 요약해줘")

    assert all(f"‘{header}’:" in answer.answer for header in ("Event Date", "Event Type", "Description"))


def test_the_row_identity_column_does_not_narrow_the_scope() -> None:
    summary, _ = table_fixture([(1, 1, MATRIX)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="frequencies", table_id=table.id, column_scope="all_attributes",
                            identity_column_ids=["A"])

    assert named_column_scope("Headline 기준 항목별 요약", plan, table, [table]) == plan


def test_a_date_without_a_time_of_day_is_shown_as_the_date() -> None:
    assert _label(datetime(2025, 12, 9)) == "2025-12-09"
    assert _label("2025-12-09T00:00:00") == "2025-12-09"
    assert _label(datetime(2025, 12, 9, 8, 40)) == "2025-12-09 08:40:00"
