import pytest

from tests.support.semantic_claim_fixtures import answer, evidence, grid, observation


@pytest.mark.parametrize("period", [
    "2024년 10월", "2024-10-01", "2024년 9월 2일", "2024-09-02", "October 2024",
    "2024년 13월", "2024년 10월 이후", "2024년 8월 이전",
])
def test_raw_observation_cannot_substitute_another_month_or_day(period):
    result = answer(grid(), [observation()], question=f"장비-A의 {period} 네트워크 안정 값은?")
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"


@pytest.mark.parametrize("period", ["2024년", "2024년 9월", "2024-09-01", "September 2024"])
def test_exact_source_period_still_allows_a_literal_observation(period):
    result = answer(grid(), [observation()], question=f"장비-A의 {period} 네트워크 안정 값은?")
    assert result.status == "limited"
    assert "‘x’" in result.answer


@pytest.mark.parametrize("question", [
    "장비-A가 아닌 장비의 네트워크 안정 값은?",
    "장비-A를 제외한 네트워크 안정 값은?",
    "장비-A 말고 다른 장비의 네트워크 안정 값은?",
    "장비-C의 네트워크 안정 값은?",
    "장비-C 네트워크 안정 값은?",
    "OtherCorp의 네트워크 안정 값은?",
    "장비C 네트워크 안정 값은?",
    "장비99 네트워크 안정 값은?",
])
def test_excluded_or_nonexistent_requested_entity_cannot_receive_another_rows_value(question):
    result = answer(grid(), [observation()], question=question)
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"


@pytest.mark.parametrize("question", [
    "매출 100 초과인 지역을 알려줘", "매출 100 미만인 지역을 알려줘", "매출이 200 이상인 지역은?",
    "매출이 100이 아닌 지역을 보여줘", "매출 >100인 지역은?", "매출 >= 200인 지역은?",
    "매출이 100 이하인 지역은?", "매출 상위 1개 지역은?",
    "매출이 100만원 초과인 지역은?", "매출이 가장 높은 지역은?",
])
def test_raw_observations_cannot_claim_an_unexecuted_population_filter(question):
    cells = [evidence("A1", "지역"), evidence("B1", "매출"), evidence("A2", "동부", "지역"),
             evidence("B2", 100, "매출"), evidence("A3", "서부", "지역"), evidence("B3", 200, "매출")]
    claims = [{"kind": "cell_value", "value_reference": "Data!B2", "subject_reference": "Data!A2",
               "property_reference": "Data!B1"}]
    result = answer(cells, claims, question=question)
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"


def test_date_only_in_a_description_does_not_prove_the_requested_period():
    cells = [evidence("B2", 10, "2024년 9월 수량")]
    result = answer(cells, [{"kind": "cell_value", "value_reference": "Data!B2"}], question="2024년 9월 수량은?")
    assert result.status == "insufficient_evidence"


@pytest.mark.parametrize("reference,status", [("Data!B2", "limited"), ("Data!B3", "insufficient_evidence")])
def test_qualified_cell_reference_is_scope_not_an_entity_identifier(reference, status):
    result = answer(grid(), [observation()], question=f"{reference} 값은?")
    assert result.status == status
    assert result.verification.level == ("source_checked" if status == "limited" else "unverified")
