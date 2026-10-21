"""Scoped growth keeps original evidence and expands identical populations."""
import pytest

from app.agent.query.scoped_derived_answers import scoped_derived_trend_answer
from tests.tabular_query_fixtures import table_fixture


def answer(rows, question, headers=("Date", "지역", "인원")):
    summary, index = table_fixture([(1, 1, [list(headers), *rows])])
    return scoped_derived_trend_answer(question, summary, index)


def rows():
    return [[date, region, amount] for region, values in
            [("동부", [100, 100, 100, 120, 110, 90]), ("서부", [200, 200, 200, 180, 220, 240])]
            for date, amount in zip(["2023-01-31", "2023-02-28", "2023-03-31",
                                     "2024-01-31", "2024-02-29", "2024-03-31"], values)]


def test_grouped_yoy_expands_baseline_and_shows_each_exact_rate():
    result = answer(rows(), "2024년 1분기 지역별 인원 전년 동기 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"
    for value in ["2024-01-31: 20%", "2024-03-31: -10%", "2024-01-31: -10%", "2024-03-31: 20%"]:
        assert value in result.answer
    assert {100, 200, 90, 240} <= {cell.value for cell in result.evidence}
    assert "동부" in result.answer and "서부" in result.answer


def test_filtered_growth_cannot_pick_other_regions_baseline():
    data = rows()
    data = [row for row in data if row != ["2023-02-28", "동부", 100]]
    result = answer(data, "2024년 1분기 동부 지역만 인원 전년 동기 대비 증감률 추이")
    assert result.status == "insufficient_evidence", result.model_dump()


def test_comparison_word_is_enough_for_grouped_rate_request():
    result = answer(rows(), "2024년 지역별 인원 전년 동기 대비 증가율을 비교해줘")
    assert result.status == "answered", result.model_dump()
    assert "2024-03-31: -10%" in result.answer


def test_numeric_condition_does_not_validate_stale_values_outside_baseline_window():
    data = [["2020-01-31", "동부", None], *rows()]
    result = answer(data, "2024년 1분기 지역별 인원 50 이상 전년 동기 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()


def test_group_only_present_outside_requested_output_is_not_a_phantom_current_group():
    data = [*rows(), ["2023-01-31", "과거지역", None], ["2023-02-28", "과거지역", None]]
    result = answer(data, "2024년 1분기 지역별 인원 전년 동기 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert "과거지역" not in result.answer


def test_previous_numeric_baseline_ignores_values_older_than_immediately_matching_prior():
    data = [["2020-01-31", "동부", None], ["2023-12-31", "동부", 100],
            ["2024-01-31", "동부", 120], ["2024-02-29", "동부", 180]]
    result = answer(data, "2024년 지역별 인원 50 이상 이전 시점 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert "20% → 50%" in result.answer


def test_unknown_numeric_filter_value_inside_output_window_still_blocks():
    data = rows()
    data[4][2] = None
    result = answer(data, "2024년 지역별 인원 50 이상 전년 동기 대비 증감률 추이")
    assert result.status == "insufficient_evidence", result.model_dump()


def test_source_category_called_previous_month_does_not_change_rate_basis_or_drop_filter():
    data = [[date, category, value] for date, value in
            [("2024-01-31", 100), ("2024-03-31", 120), ("2024-05-31", 180)]
            for category in ("전월", "다른지역")]
    result = answer(data, "전월 지역 인원 이전 시점 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert "20% → 50%" in result.answer
    assert "다른지역" not in {cell.value for cell in result.evidence}


def test_growth_words_in_metric_label_are_not_a_derived_operator():
    assert answer(rows(), "지역별 Revenue Growth 추이", ("Date", "지역", "Revenue Growth")) is None


def test_temporal_sheet_name_does_not_select_a_rate_baseline():
    matrix = [["Date", "Team", "Headcount"], ["2024-01-31", "A", 100],
              ["2024-03-31", "A", 120], ["2024-05-31", "A", 180]]
    summary, index = table_fixture([(1, 1, matrix)], sheet_name="전월")
    result = scoped_derived_trend_answer("'전월' 시트에서 Team별 Headcount 증감률 추이", summary, index)
    assert result.status == "answered", result.model_dump()
    assert "20% → 50%" in result.answer
    assert "이전 관측값" in result.answer


def test_temporal_sheet_label_does_not_erase_separate_explicit_month_baseline():
    matrix = [["Date", "Team", "Headcount"], ["2024-01-31", "A", 100],
              ["2024-03-31", "A", 120], ["2024-05-31", "A", 180]]
    summary, index = table_fixture([(1, 1, matrix)], sheet_name="전월")
    result = scoped_derived_trend_answer("'전월' 시트에서 Team별 Headcount 전월 대비 증감률 추이", summary, index)
    assert result.status == "insufficient_evidence", result.model_dump()


def test_explicit_aggregate_cites_original_values_not_calculated_cells():
    data = [[date, region, value] for date, values in
            [("2024-01-31", (10, 20)), ("2024-02-29", (20, 40)), ("2024-03-31", (30, 60))]
            for region in ("동부", "서부") for value in values]
    result = answer(data, "지역별 인원 합계 이전 시점 대비 증감률 추이")
    assert result.status == "answered", result.model_dump()
    assert "100% → 50%" in result.answer
    assert 90 not in {cell.value for cell in result.evidence}


@pytest.mark.parametrize("question", [
    "지역별 인원 증감률 추이 퇴사자 제외", "지역별 인원 증감률 추이 예측",
    "지역별 인원 전월 전년 동기 대비 증감률 추이", "지역별 인원 비중 증감률 추이",
])
def test_unbound_or_extra_operation_never_verified(question):
    result = answer(rows(), question)
    assert result and result.status == "insufficient_evidence", result
    assert result.verification.level != "request_checked"


@pytest.mark.parametrize("bad", [None, 0, -1, "=EXTERNAL()"])
def test_unusable_baseline_never_verified(bad):
    data = rows()
    data[0][2] = bad
    result = answer(data, "2024년 1분기 지역별 인원 전년 동기 대비 증감률 추이")
    assert result and result.status == "insufficient_evidence", result
