import pytest

from app.agent.query.question_formula_sources import prepare_formula_sources
from tests.test_question_formula_integration import answer, source_fixture


@pytest.mark.parametrize("formula, expected", [
    ('=SUMIF(A2:A4,"Alpha",B2:B4)', 40),
    ('=SUMIFS(B2:B4,A2:A4,"Alpha",C2:C4,1)', 40),
    ('=COUNTIFS(A2:A4,"Alpha",C2:C4,1)', 2),
    ('=XLOOKUP("Beta",A2:A4,B2:B4)', 20),
    ('=INDEX(B2:B4,MATCH("Beta",A2:A4,0))', 20),
])
def test_recovered_reference_function_answers_are_derived_not_fully_verified(formula, expected):
    summary, index = source_fixture([["Group", "Amount", "Flag", "Calculated"],
                                    ["Alpha", 10, 1, formula], ["Beta", 20, 2], ["Alpha", 30, 1]])
    original = repr(summary), repr(index)
    sources = prepare_formula_sources(summary, index)
    assert sources.resolutions["Data!D2"].value == expected
    result = answer("Data!D2의 값은 얼마야?", summary, index)
    assert str(expected) in result.answer
    assert result.status == "limited" and result.verification.level == "source_checked"
    assert "bounded_recalculation" in result.verification.checks
    assert "request_alignment" not in result.verification.checks
    assert any("저장된 결과가 없는 수식" in limitation for limitation in result.limitations)
    assert len(result.evidence) > 1
    assert (repr(summary), repr(index)) == original


@pytest.mark.parametrize("formula", [
    '=IFERROR(SUMIF(A2:A3,"Alpha",B2:B3),0)',
    '=IFERROR(XLOOKUP("Alpha",A2:A3,B2:B3),0)',
])
def test_unavailable_lookup_or_aggregate_cannot_be_shown_as_verified_zero(formula):
    summary, index = source_fixture([["Group", "Amount", "Calculated"],
                                    ["Alpha", "=_xll.Remote()", formula], ["Beta", 20]])
    result = answer("Data!C2의 값은 얼마야?", summary, index)
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"
    assert "새로 고친" in result.answer
