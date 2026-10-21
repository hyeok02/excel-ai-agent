"""Two-table trajectory oracles retain original values on both join sides."""
from dataclasses import replace

import pytest

from app.agent.query.joined_trend_answers import joined_trend_answer
from tests.support.large_workbook_fixtures import offline, parsed, workbook

QUESTION = "이력과 부서정보를 부서코드로 연결해서 서울 사업장 부서별 월별 인원 추이를 보여줘"


def sources():
    return {"이력": [["Date", "부서코드", "인원"],
                    ["2024-03-31", "D1", 90], ["2024-01-31", "D1", 100], ["2024-02-29", "D1", 80],
                    ["2024-03-31", "D2", 50], ["2024-01-31", "D2", 40], ["2024-02-29", "D2", 60],
                    ["2024-01-31", "D3", 9999], ["2024-02-29", "D3", None]],
            "부서정보": [["부서코드", "부서", "사업장"], ["D1", "서비스", "서울"],
                         ["D2", "개발", "서울"], ["D3", "영업", "부산"]]}


def answer(sheets=None, question=QUESTION, book=None):
    summary, index, _ = parsed(book or workbook(sheets or sources()))
    return joined_trend_answer(question, summary, index)


def checked(result):
    assert result is not None
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked", result.model_dump()


def unsafe(result):
    assert result is not None
    assert result.status != "answered", result.model_dump()
    assert result.verification.level != "request_checked", result.model_dump()


def test_joined_groups_filter_before_metric_validation_and_keep_chronology():
    result = answer()
    checked(result)
    assert "100명 → 90명" in result.answer and "40명 → 50명" in result.answer
    assert "반등" in result.answer and "하락 전환" in result.answer
    assert "9,999" not in result.answer
    assert "typed_join_keys" in result.verification.checks
    originals = {(name, f"{column}{row}"): value for name, matrix in sources().items()
                 for row, values in enumerate(matrix, 1) for column, value in zip("ABC", values)}
    assert all(cell.value == originals[cell.sheet_name, cell.reference] for cell in result.evidence)
    assert {("이력", "B2"), ("부서정보", "A2"), ("부서정보", "C2")} <= {
        (cell.sheet_name, cell.reference) for cell in result.evidence}


def test_unique_shared_exact_key_is_a_disclosed_candidate_until_explicitly_requested():
    result = answer(question=QUESTION.replace("부서코드로 ", ""))
    unsafe(result)
    assert result.status == "limited" and "부서코드" in result.answer
    assert any("후보 기준" in limitation for limitation in result.limitations)
    sheets = sources()
    sheets["이력"][0][1] = sheets["부서정보"][0][0] = "연결ID"
    checked(answer(sheets, QUESTION.replace("부서코드", "연결ID")))


def test_explicit_date_scope_excludes_unknown_keys_before_join():
    sheets = sources()
    sheets["이력"].append(["2020-01-31", "archived", None])
    checked(answer(sheets, QUESTION.replace("월별", "2024년 월별")))
    unsafe(answer(sheets))


def test_explicit_left_condition_can_exclude_an_unmatched_row():
    sheets = sources()
    sheets["이력"][0].append("상태")
    for row in sheets["이력"][1:]:
        row.append("유효")
    sheets["이력"].append(["2024-01-31", "archived", None, "취소"])
    checked(answer(sheets, QUESTION.replace("서울", "유효 상태만 서울")))


def test_joined_year_over_year_growth_uses_original_baselines():
    sheets = sources()
    sheets["이력"] = [sheets["이력"][0], ["2023-01-31", "D1", 100], ["2023-02-28", "D1", 200],
                     ["2024-01-31", "D1", 120], ["2024-02-29", "D1", 220]]
    result = answer(sheets, QUESTION.replace("월별 인원 추이", "2024년 인원 전년 동기 대비 증가율 추이"))
    checked(result)
    assert "20%" in result.answer and "10%" in result.answer
    assert {"C2", "C3", "C4", "C5"} <= {cell.reference for cell in result.evidence if cell.sheet_name == "이력"}


def test_join_word_in_actual_single_table_metric_does_not_hijack_route():
    sheets = {"이력": [["Date", "연결 인원"], ["2024-01-31", 100], ["2024-02-29", 120]]}
    assert answer(sheets, "연결 인원 추이를 보여줘") is None


def test_explicit_join_preserves_join_word_in_actual_metric():
    sheets = sources()
    sheets["이력"][0][2] = "연결 인원"
    checked(answer(sheets, QUESTION.replace("월별 인원", "월별 연결 인원")))


def test_join_word_in_actual_category_does_not_hijack_route():
    sheets = {"이력": [["Date", "상태", "인원"], ["2024-01-31", "연결", 100], ["2024-02-29", "연결", 120]]}
    assert answer(sheets, "연결 상태만 인원 추이를 보여줘") is None


def test_joined_group_shares_keep_filtered_complete_denominator():
    result = answer(question=QUESTION.replace("월별 인원 추이", "전체 인원 비중 추이"))
    checked(result)
    assert "71.43%" in result.answer and "64.29%" in result.answer
    assert "28.57%" in result.answer and "35.71%" in result.answer
    assert "9,999" not in result.answer


def test_joined_month_end_adapter_keeps_real_values_and_addresses():
    result = answer(question=QUESTION.replace("월별 인원 추이", "월별 인원 기말값"))
    checked(result)
    assert "resampled_trend" in result.selected_tools
    assert "2024년 1월: 100명" in result.answer and "2024년 2월: 80명" in result.answer
    assert "complete_join_coverage" in result.verification.checks
