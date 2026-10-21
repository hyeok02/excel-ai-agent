"""Master metadata dates cannot masquerade as a requested fact measure."""
from tests.support.large_workbook_fixtures import offline
from tests.test_joined_trend_answers import QUESTION, answer, sources, unsafe


def test_master_updated_date_does_not_make_department_group_a_second_measure():
    sheets = sources()
    sheets["부서정보"][0].append("Updated Date")
    for day, row in enumerate(sheets["부서정보"][1:], 1):
        row.append(f"2024-01-{day:02}")
    result = answer(sheets)
    unsafe(result)
    assert result.status == "limited"
    assert "100명 → 90명" in result.answer
    assert "추이 날짜 축: 이력.Date" in result.answer and "부서정보.Updated Date" in result.answer
    assert {"D1", "D2", "D3", "D4"} <= {cell.reference for cell in result.evidence if cell.sheet_name == "부서정보"}


def test_true_second_fact_measure_is_not_silently_ignored():
    sheets = sources()
    sheets["부서정보"][0].extend(["Date", "인원"])
    for row in sheets["부서정보"][1:]:
        row.extend(["2024-01-31", 999])
    unsafe(answer(sheets))


def test_requested_master_date_is_not_silently_replaced_with_fact_date():
    sheets = sources()
    sheets["부서정보"][0].append("Updated Date")
    for row in sheets["부서정보"][1:]:
        row.append("2024-01-01")
    unsafe(answer(sheets, QUESTION.replace("월별", "Updated Date 기준 월별")))
