import pytest

from app.agent.query.index import build_workbook_data_index
from app.services.workbook_parser import parse_workbook
from tests.formula_reference_fixtures import content, source_book
from tests.test_question_formula_integration import answer


@pytest.mark.parametrize("formula", ["=SUM(Amounts)", "=SUM(Sales[Amount])"])
def test_named_and_table_formula_answers_are_source_checked_derivations_not_originals(formula):
    data = content(source_book(formula))
    summary = parse_workbook("any-file.xlsx", data)
    index = build_workbook_data_index("any-file.xlsx", data)
    before = repr(summary), repr(index)
    response = answer("Data!F1 값은?", summary, index)
    assert "60" in response.answer
    assert response.status == "limited" and response.verification.level == "source_checked"
    assert {item.reference for item in response.evidence} >= {"F1", "B2", "B3", "B4"}
    assert any("저장된 원본 계산 결과가 아닙니다" in item.description for item in response.evidence)
    assert (repr(summary), repr(index)) == before


def test_row_relative_structured_formula_answer_preserves_actual_input_cells():
    workbook = source_book()
    workbook["Data"]["D2"] = "=[@Amount]*[@Qty]"
    data = content(workbook)
    response = answer("Data!D2 값은?", parse_workbook("any.xlsx", data), build_workbook_data_index("any.xlsx", data))
    assert "20" in response.answer and response.verification.level == "source_checked"
    assert {item.reference for item in response.evidence} >= {"D2", "B2", "C2"}


@pytest.mark.parametrize("formula", ["=IFERROR(SUM(Unknown),0)", "=IFERROR(SUM(Sales[Missing]),0)"])
def test_unknown_named_or_table_reference_never_gets_verified_zero(formula):
    data = content(source_book(formula))
    response = answer("Data!F1 값은?", parse_workbook("any.xlsx", data), build_workbook_data_index("any.xlsx", data))
    assert response.status == "insufficient_evidence"
    assert response.verification.level == "unverified"
