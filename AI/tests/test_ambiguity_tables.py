from dataclasses import replace

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.ambiguity_labels import resolve_unique_column
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


def _parallel():
    return table_fixture([
        (4, 2, [["Owner", "Amount"], ["Alpha Holdings", 10], ["Bravo Holdings", 20]]),
        (4, 7, [["Fund", "Amount"], ["Gamma Fund", 70], ["Delta Fund", 80]]),
    ], sheet_name="Moved source")


def test_parallel_matching_fields_offer_actual_source_choices_without_verification():
    summary, index = _parallel()
    result = ambiguous_source_answer("Amount 합계는?", summary, index)
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"
    assert "B4:C6" in result.answer and "G4:H6" in result.answer
    assert "다시 질문:" in result.answer
    assert {"C4", "C5", "C6", "H4", "H5", "H6"} <= {cell.reference for cell in result.evidence}
    assert "원본 값 예시" in result.answer and "10" in result.answer and "80" in result.answer


def test_other_explicit_source_header_or_record_identity_resolves_parallel_table():
    summary, index = _parallel()
    for question in ["Owner 표의 Amount 합계는?", "Alpha Holdings의 Amount는?"]:
        assert ambiguous_source_answer(question, summary, index) is None


def test_exact_range_and_explicit_column_resolve_duplicate_table_fields():
    summary, index = _parallel()
    assert ambiguous_source_answer("'Moved source'!B4:C6 범위의 Amount 합계", summary, index) is None
    summary, index = table_fixture([(1, 1, [["Record", "Amount", "Amount"], ["One", 5, 9]])])
    assert ambiguous_source_answer("Amount는?", summary, index) is not None
    assert ambiguous_source_answer("'Arbitrary'!A1:C2 범위의 B열 Amount는?", summary, index) is None


def test_source_sheet_qualification_resolves_identical_labels():
    left, left_index = table_fixture([(1, 1, [["Record", "Amount"], ["First", 5]])], "North")
    right, right_index = table_fixture([(5, 4, [["Record", "Amount"], ["Second", 9]])], "South")
    summary = replace(left, sheets=[*left.sheets, *right.sheets], sheet_count=2)
    index = replace(left_index, rows=(*left_index.rows, *right_index.rows))
    assert ambiguous_source_answer("Amount 합계", summary, index) is not None
    assert ambiguous_source_answer("South 시트 Amount 합계", summary, index) is None


def test_full_unit_qualified_field_resolves_but_generic_metric_does_not():
    summary, index = table_fixture([(1, 1, [
        ["Record", "Revenue (USD)", "Revenue (EUR)"], ["One", 10, 20],
    ])])
    result = ambiguous_source_answer("Revenue 합계", summary, index)
    assert "Revenue (USD)" in result.answer and "Revenue (EUR)" in result.answer
    assert ambiguous_source_answer("Revenue (EUR) 합계", summary, index) is None


def test_summary_structure_and_join_requests_are_not_globally_blocked():
    summary, index = _parallel()
    for question in ["이 파일 뭐야?", "Amount 표들을 조인해줘", "어떤 시트가 있어?"]:
        assert ambiguous_source_answer(question, summary, index) is None
    intent = QuestionIntent(True, "summary")
    assert ambiguous_source_answer("Amount를 설명해줘", summary, index, intent) is None


def test_normalized_unique_source_headers_bind_without_fuzzy_matching():
    summary, _ = table_fixture([(1, 1, [["Record ID", "Ｎｅｔ\u00a0Amount"], ["One", 10]])])
    table = build_query_tables(summary)[0]
    assert resolve_unique_column("net-amount", table) == "B"
    assert resolve_unique_column("Amount", table) is None
    assert resolve_unique_column("Net Amount Estimate", table) is None
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["net amount"])
    assert bind_tabular_plan(plan, table).column_ids == ["B"]


def test_normalization_collisions_never_choose_first_source_column():
    summary, _ = table_fixture([(1, 1, [["Record", "Net Amount", "Net-Amount"], ["One", 10, 20]])])
    table = build_query_tables(summary)[0]
    assert resolve_unique_column("NET_AMOUNT", table) is None
    assert resolve_unique_column("Net Amount", table) == "B"
    assert resolve_unique_column("Unlisted metric", table) is None
