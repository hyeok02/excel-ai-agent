"""Group state keeps typed dimensions and computes statistics from source values."""
import pytest

from tests.support.grouped_ranking_fixtures import grouped_plan, line_with, source
from tests.support.large_workbook_fixtures import ask, assert_stream_checked, offline, tiny_caps


@pytest.mark.parametrize("statistic,question,expected", [
    ("sum", "합계", "합계 16"), ("average", "평균", "평균 8"),
    ("min", "최솟값", "최솟값 -8"), ("max", "최댓값", "최댓값 24"),
    ("all", "통계", "합계 16"),
])
def test_all_supported_group_statistics_include_values_after_prefix(tiny_caps, statistic, question, expected):
    matrix = [["Record", "Amount", "Department"], ["A", -8, "Alpha"],
              ["B", 4, "Beta"], ["C", 24, "Alpha"], ["D", 10, "Beta"]]
    summary, index, _ = source(matrix)
    answer = ask(f"Records 시트 Department별 Amount {question} 알려줘", summary, index,
                 grouped_plan(summary, statistic=statistic))
    assert_stream_checked(answer)
    assert expected in line_with(answer, "Alpha")
    if statistic == "all":
        line = line_with(answer, "Alpha")
        assert "평균 8" in line and "최솟값 -8" in line and "최댓값 24" in line


def test_group_keys_do_not_conflate_boolean_number_text_and_blank(tiny_caps):
    matrix = [["Record", "Amount", "Department"], ["A", 10, True], ["B", 20, 1],
              ["C", 30, "1"], ["D", 40, None]]
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Department별 Amount 합계 알려줘", summary, index, grouped_plan(summary))
    assert_stream_checked(answer)
    for total in (10, 20, 30, 40):
        assert f"합계 {total}" in answer.answer
    assert "빈칸" in answer.answer
    assert "합계 60" not in answer.answer and "합계 100" not in answer.answer


def test_two_group_dimensions_do_not_merge_same_label_under_other_dimension(tiny_caps):
    summary, index, _ = source()
    plan = grouped_plan(summary, group_by=["C", "D"])
    answer = ask("Records 시트 Department와 State별 Amount 합계 알려줘", summary, index, plan)
    assert_stream_checked(answer)
    lines = [line for line in answer.answer.splitlines() if "Alpha" in line]
    assert len(lines) == 2, answer.model_dump()
    assert any("active" in line and "합계 24" in line for line in lines)
    assert any("inactive" in line and "합계 -8" in line for line in lines)


def test_blank_numeric_cells_are_counted_not_fabricated_as_zero_observations(tiny_caps):
    matrix = [["Record", "Amount", "Department"], ["A", 10, "Alpha"],
              ["B", None, "Alpha"], ["C", 30, "Alpha"], ["D", 8, "Beta"]]
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 Department별 Amount 평균 알려줘", summary, index,
                 grouped_plan(summary, statistic="average"))
    assert_stream_checked(answer)
    assert "평균 20" in line_with(answer, "Alpha")
    assert "빈칸 1건" in line_with(answer, "Alpha")


def test_group_filter_with_no_matches_is_explicit_not_a_zero_group(tiny_caps):
    from tests.support.large_workbook_fixtures import equal
    summary, index, _ = source()
    answer = ask("Records 시트 State가 absent인 Department별 Amount 합계 알려줘", summary, index,
                 grouped_plan(summary, filters=[equal("D", "absent")]))
    assert_stream_checked(answer)
    assert any(word in answer.answer for word in ("없", "0건"))
    assert "합계 0" not in answer.answer
