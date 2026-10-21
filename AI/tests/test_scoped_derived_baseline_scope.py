"""Exact rate operands must not absorb unrelated intervening history."""
import pytest

from tests.test_scoped_derived_growth import answer, rows


@pytest.mark.parametrize("value", [None, 0, -1, 999])
@pytest.mark.parametrize("reverse", [False, True])
def test_yoy_ignores_irrelevant_history_between_baseline_and_output(value, reverse):
    data = [*rows(), ["2023-07-31", "동부", value]]
    if reverse:
        data.reverse()
    result = answer(data, "2024년 1분기 지역별 인원 전년 동기 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"
    assert "20% → -10%" in result.answer and "-10% → 20%" in result.answer
    assert "2023-07-31" not in {cell.value for cell in result.evidence}


def test_monthly_growth_ignores_nonmatching_days_in_expanded_baseline_month():
    data = [["2024-01-15", "동부", None], ["2024-01-31", "동부", 100],
            ["2024-02-29", "동부", 120], ["2024-03-31", "동부", 180]]
    result = answer(data, "2024년 2월부터 3월까지 지역별 인원 전월 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert "20% → 50%" in result.answer
    assert "2024-01-15" not in {cell.value for cell in result.evidence}


@pytest.mark.parametrize("group", [None, ""])
def test_irrelevant_historic_row_does_not_need_a_group_identity(group):
    result = answer([*rows(), ["2023-07-31", group, None]],
                    "2024년 1분기 지역별 인원 전년 동기 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"


def test_missing_group_on_a_required_baseline_date_is_not_silently_discarded():
    result = answer([*rows(), ["2023-01-31", None, 100]],
                    "2024년 1분기 지역별 인원 전년 동기 대비 증감률 추이")
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level != "request_checked"


@pytest.mark.parametrize("value", [None, 0, -1])
def test_required_baseline_is_still_validated(value):
    data = [*rows(), ["2023-07-31", "동부", None]]
    data[0][2] = value
    result = answer(data, "2024년 1분기 지역별 인원 전년 동기 대비 증감률 추이")
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level != "request_checked"


def test_each_group_keeps_only_its_own_required_baseline_dates():
    data = [["2023-01-31", "동부", 100], ["2023-02-28", "동부", 100],
            ["2024-01-31", "동부", 120], ["2024-02-29", "동부", 150],
            ["2023-02-28", "서부", 200], ["2023-03-31", "서부", 200],
            ["2024-02-29", "서부", 220], ["2024-03-31", "서부", 240],
            ["2023-03-31", "동부", None], ["2023-01-31", "서부", None]]
    result = answer(data, "2024년 1분기 지역별 인원 전년 동기 대비 증감률 추이")
    assert result.status == "limited", result.model_dump()
    assert "20% → 50%" in result.answer and "10% → 20%" in result.answer
    assert any("그룹별 원본 날짜" in reason for reason in result.limitations)
    assert result.verification.level != "request_checked"


def test_join_does_not_require_an_unrelated_intervening_master_key():
    from tests.test_joined_trend_answers import answer as joined_answer
    sheets = {"이력": [["Date", "부서코드", "인원"],
                       ["2023-01-31", "A", 100], ["2023-02-28", "A", 100],
                       ["2023-07-31", "ARCHIVED", None],
                       ["2024-01-31", "A", 120], ["2024-02-29", "A", 150]],
              "부서정보": [["부서코드", "부서", "사업장"], ["A", "서비스", "서울"]]}
    question = "이력과 부서정보를 부서코드로 연결해서 2024년 1분기 서울 사업장만 부서별 인원 전년 동기 대비 증감률 추이"
    result = joined_answer(sheets, question)
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"
    assert "20% → 50%" in result.answer
    assert "ARCHIVED" not in {cell.value for cell in result.evidence}
