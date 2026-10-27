import pytest
from app.agent.query.source_lookup_answers import source_lookup_answer
from app.agent.query.question_formula_sources import prepare_formula_sources
from tests.support.large_workbook_fixtures import parsed, workbook
from tests.test_source_lookup_answers import ask, fixture


@pytest.mark.parametrize("suffix", ["셀의 값을 알려줘", "셀의 저장된 계산 결과는 얼마야?",
                                    "범위의 내용을 보여주세요", "의 수치는 얼마인가요?"])
def test_attached_particles_and_stored_result_do_not_redirect_to_other_sheet(suffix):
    summary, index, _ = parsed(workbook({"12 month Archive": [["Item", "Amount"], ["a", 731.25]],
                                       "Other": [["Note", "Cost"], ["REF! B2", 999]]}))
    response = ask("'12 month Archive'!B2 " + suffix, summary, index)
    assert "731.25" in response.answer
    assert response.status == "answered" and response.verification.level == "request_checked"
    assert {(item.sheet_name, item.reference) for item in response.evidence} == {("12 month Archive", "B2")}


@pytest.mark.parametrize("suffix", ["셀의 합계에 5 더해줘", "셀의 값이 50 이상인 행만",
                                    "셀의 계산 결과가 맞는 이유는?", "셀의 값을 USD로 환산해줘"])
def test_particle_support_does_not_drop_remaining_operations(suffix):
    summary, index, _ = fixture()
    assert source_lookup_answer("Records!B10 " + suffix, prepare_formula_sources(summary, index)) is None
