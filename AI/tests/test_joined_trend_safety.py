"""Unsafe joins must never be presented as complete, verified trajectories."""
from dataclasses import replace

import pytest

from app.agent.query.joined_trend_answers import joined_trend_answer
from tests.support.large_workbook_fixtures import offline, parsed, workbook
from tests.test_joined_trend_answers import QUESTION, answer, checked, sources, unsafe


@pytest.mark.parametrize("key", [None, "MISSING", 1, "d1", "01", "=EXTERNAL_KEY()"])
def test_null_unmatched_typed_or_uncached_detail_keys_are_not_guessed(key):
    sheets = sources()
    sheets["이력"][1][1] = key
    unsafe(answer(sheets))


def test_relevant_duplicate_master_keys_cannot_multiply_counts_even_if_identical():
    sheets = sources()
    sheets["부서정보"].append(list(sheets["부서정보"][1]))
    unsafe(answer(sheets))


def test_unreferenced_duplicate_master_key_does_not_block_known_population():
    sheets = sources()
    sheets["부서정보"].extend([["UNUSED", "미사용", "서울"], ["UNUSED", "미사용", "부산"]])
    checked(answer(sheets))


def test_duplicate_detail_dates_are_not_silently_deduplicated():
    sheets = sources()
    sheets["이력"].append(list(sheets["이력"][1]))
    unsafe(answer(sheets))


def test_explicit_sum_does_not_attach_calculated_value_to_original_cell():
    sheets = sources()
    sheets["이력"].append(["2024-01-31", "D1", 10])
    result = answer(sheets, QUESTION.replace("월별 인원", "인원 합계"))
    checked(result)
    assert "110명 → 90명" in result.answer
    assert all(cell.value != 110 for cell in result.evidence)


@pytest.mark.parametrize("side", ["이력", "부서정보"])
def test_hidden_rows_and_columns_cannot_receive_complete_badge(side):
    book = workbook(sources())
    book[side].row_dimensions[2].hidden = True
    unsafe(answer(book=book))
    book = workbook(sources())
    book[side].column_dimensions["B"].hidden = True
    unsafe(answer(book=book))


def test_truncated_source_without_readback_never_uses_partial_join():
    summary, index, _ = parsed(workbook(sources()))
    index = replace(index, rows=index.rows[:-3], truncated=True,
                    truncated_sheet_names=frozenset({"부서정보"}), source_provider=None)
    unsafe(joined_trend_answer(QUESTION, summary, index))


@pytest.mark.parametrize("change", [
    lambda q: q.replace("서울", "대전"),
    lambda q: q.replace("부서코드로", "없는키로"),
    lambda q: q + " 내년 인원도 예측해줘",
    lambda q: q.replace("서울", "서울 또는 부산"),
])
def test_unresolved_key_predicate_or_operation_must_not_be_ignored(change):
    unsafe(answer(question=change(QUESTION)))


def test_multiple_tables_or_date_axes_require_explicit_source_resolution():
    sheets = sources()
    sheets["다른표"] = [["부서코드", "부서"], ["D1", "다른부서"]]
    unsafe(answer(sheets, "부서코드로 연결해서 서울 사업장 부서별 인원 추이"))
    checked(answer(sheets))
    sheets = sources()
    sheets["이력"][0].append("기준일")
    for row in sheets["이력"][1:]:
        row.append(row[0])
    unsafe(answer(sheets))


def test_joined_aggregation_without_trend_keyword_is_intercepted():
    result = answer(question=QUESTION.replace("월별 인원 추이를", "월별 인원 합계를"))
    assert result is not None
    assert "joined_trend" in result.selected_tools


def test_literal_category_named_previous_month_is_not_a_rate_operator():
    sheets = sources()
    sheets["부서정보"][1][1] = "전월"
    question = QUESTION.replace("부서별 월별 인원 추이", '"전월" 부서별 인원 증감률 추이')
    result = answer(sheets, question)
    checked(result)
    assert "개발" not in result.answer
    assert "전월 대비" not in result.answer
    assert "-20%" in result.answer and "12.5%" in result.answer


def test_absolute_yoy_join_ignores_archived_unmatched_rows_but_requires_baseline_matches():
    sheets = sources()
    sheets["이력"] = [sheets["이력"][0], ["2023-01-31", "D1", 100], ["2023-02-28", "D1", 200],
                     ["2024-01-31", "D1", 120], ["2024-02-29", "D1", 220], ["2020-01-31", "ARCHIVED", None]]
    question = QUESTION.replace("월별 인원 추이", "2024년 인원 전년 동기 대비 증가율 추이")
    result = answer(sheets, question)
    checked(result)
    assert "20%" in result.answer and "10%" in result.answer
    sheets["이력"][1][1] = "MISSING_BASELINE"
    unsafe(answer(sheets, question))


def test_source_sheet_name_is_not_a_derivative_baseline_operator():
    sheets = sources()
    sheets["전월이력"] = sheets.pop("이력")
    question = QUESTION.replace("이력과", "전월이력과").replace("월별 인원 추이", "인원 증감률 추이")
    result = answer(sheets, question)
    checked(result)
    assert "전월 대비" not in result.answer
    assert result.question == question
