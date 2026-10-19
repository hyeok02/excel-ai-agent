"""Post-aggregation filters and denominators are not source-row predicates."""
from dataclasses import replace

import pytest

from tests.support.advanced_qna_fixtures import checked, condition, group_line, group_plan, has_group, source
from tests.support.large_workbook_fixtures import ask, equal, offline, tiny_caps


@pytest.mark.parametrize("provider", [False, True])
def test_having_uses_group_total_not_individual_row_threshold(provider):
    summary, index, _ = source()
    if not provider:
        index = replace(index, source_provider=None)
    plan = group_plan(summary, having=[condition(70)])
    answer = ask("Records 시트 Department별 Amount 합계가 70 초과인 그룹 보여줘", summary, index, plan)
    checked(answer, scan=False)
    assert "합계 75" in group_line(answer, "Alpha")
    assert "합계 90" in group_line(answer, "Beta")
    assert not has_group(answer.answer, "Gamma")


@pytest.mark.parametrize("operator,word,expected", [
    ("greater_than", "초과", ("Beta",)),
    ("greater_than_or_equal", "이상", ("Alpha", "Beta")),
    ("less_than", "미만", ("Gamma",)),
    ("less_than_or_equal", "이하", ("Alpha", "Gamma")),
    ("equals", "같은", ("Alpha",)),
])
def test_having_boundary_operators_are_exact(tiny_caps, operator, word, expected):
    summary, index, _ = source()
    answer = ask(f"Records 시트 Department별 Amount 합계가 75 {word} 그룹 보여줘", summary, index,
                 group_plan(summary, having=[condition(75, operator=operator)]))
    checked(answer, scan=True)
    for group in ("Alpha", "Beta", "Gamma"):
        assert has_group(answer.answer, group) == (group in expected), answer.model_dump()


def test_having_filters_aggregates_after_source_row_filters(tiny_caps):
    summary, index, _ = source()
    plan = group_plan(summary, filters=[equal("E", "active")], having=[condition(50)])
    answer = ask("Records 시트 State가 active인 Department별 Amount 합계가 50 초과인 그룹 보여줘",
                 summary, index, plan)
    checked(answer, scan=True)
    assert "합계 65" in group_line(answer, "Alpha")
    assert not has_group(answer.answer, "Beta")


def share_source():
    return source([["Record", "Amount", "Department"], ["First", 40, "Alpha"],
                   ["Second", 20, "Alpha"], ["Third", 30, "Beta"], ["Last", 10, "Gamma"]])


def test_share_denominator_precedes_having_and_top_n(tiny_caps):
    summary, index, _ = share_source()
    plan = group_plan(summary, share_of_total=True, having=[condition(50)], order_by="B", limit=1)
    answer = ask("Records 시트 Department별 Amount 합계가 50 초과인 그룹의 전체 비중 상위 1개 보여줘",
                 summary, index, plan)
    checked(answer, scan=True)
    line = group_line(answer, "Alpha")
    assert "60%" in line and "100%" not in line, answer.model_dump()


def test_share_threshold_is_percentage_of_full_eligible_population(tiny_caps):
    summary, index, _ = share_source()
    plan = group_plan(summary, share_of_total=True,
                      having=[condition(20, column=None, target="share", unit="percent")])
    answer = ask("Records 시트 Department별 Amount 합계의 전체 비중이 20% 초과인 그룹 보여줘",
                 summary, index, plan)
    checked(answer, scan=True)
    assert "60%" in group_line(answer, "Alpha")
    assert "30%" in group_line(answer, "Beta")
    assert not has_group(answer.answer, "Gamma")


def test_count_having_is_not_a_measure_threshold(tiny_caps):
    summary, index, _ = source()
    plan = group_plan(summary, operation="row_count", columns=(),
                      having=[condition(3, column=None, operator="greater_than_or_equal")])
    answer = ask("Records 시트 Department별 행 개수가 3 이상인 그룹 보여줘", summary, index, plan)
    checked(answer, scan=True)
    assert "4건" in group_line(answer, "Alpha")
    assert "3건" in group_line(answer, "Beta")
    assert not has_group(answer.answer, "Gamma")


def test_having_average_is_computed_from_all_group_rows(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 Department별 Amount 평균이 25 초과인 그룹 보여줘", summary, index,
                 group_plan(summary, statistic="average", having=[condition(25)]))
    checked(answer, scan=True)
    assert "평균 30" in group_line(answer, "Beta")
    assert not has_group(answer.answer, "Alpha") and not has_group(answer.answer, "Gamma")


def test_count_share_uses_total_rows_not_number_of_groups(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 Department별 행 개수의 전체 비중 알려줘", summary, index,
                 group_plan(summary, operation="row_count", columns=(), share_of_total=True))
    checked(answer, scan=True)
    assert "50%" in group_line(answer, "Alpha")
    assert "37.5%" in group_line(answer, "Beta")
    assert "12.5%" in group_line(answer, "Gamma")
