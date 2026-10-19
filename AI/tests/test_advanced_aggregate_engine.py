"""Complete-population aggregate semantics without model or network calls."""
import pytest

from app.agent.query.grouped_tabular_results import GroupedAccumulator
from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow, QueryTable
from app.agent.query.tabular_query_models import TabularQueryPlan


def accumulator(**changes):
    fields = dict(operation="numeric_summary", table_id="t", group_by=["A"],
                  column_ids=["B"], statistic="sum")
    fields.update(changes)
    table = QueryTable("t", "Sheet", "A1:C100", tuple(
        QueryColumn(key, name, f"Sheet!{key}1", ())
        for key, name in [("A", "Group"), ("B", "Amount"), ("C", "Customer")]), (), True)
    return GroupedAccumulator(TabularQueryPlan(**fields), table)


def row(group, value, customer="customer", **kwargs):
    return QueryRow(2, {"A": group, "B": value, "C": customer}, **kwargs)


def condition(value, operator="greater_than", **changes):
    return dict(column_id="B", operator=operator, value=value, **changes)


def test_having_applies_to_full_group_not_individual_rows():
    result = accumulator(having=[condition(100)], order_by="B", limit=1)
    for item in [row("tailwinner", 60), row("other", 110), row("tailwinner", 60)]:
        assert result.add(item)
    text, _ = result.render()
    assert '"tailwinner"' in text and '"other"' not in text and "합계 120" in text
    assert "집계 후 조건을 만족하는 그룹은 2개" in text


def test_weighted_average_having_uses_rows_not_partial_average():
    result = accumulator(statistic="average", having=[condition(20)])
    for value in [10, 10, 10, 100]:
        assert result.add(row("correct", value))
    assert "평균 32.5" in result.render()[0]


def test_share_denominator_precedes_having_rank_and_limit():
    result = accumulator(having=[condition(15)], share_of_total=True, order_by="B", limit=1)
    for name, value in [("large", 70), ("middle", 20), ("small", 10)]:
        assert result.add(row(name, value))
    text, _ = result.render()
    assert "분자 70 / 분모 100" in text and "비중 약 70%" in text
    assert '"middle"' not in text and '"small"' not in text


def test_share_predicate_is_exact_not_based_on_rounded_percentage():
    result = accumulator(share_of_total=True, having=[dict(target="share", value=33.33333333333333,
                         operator="greater_than", value_unit="percent")])
    assert result.add(row("one", 1)) and result.add(row("two", 2))
    text, _ = result.render()
    assert '"one"' in text and '"two"' in text


@pytest.mark.parametrize("values", [(0, 0), (-1, 2), (None, 5)])
def test_invalid_share_population_never_becomes_verified_zero(values):
    result = accumulator(share_of_total=True, order_by="B", limit=1)
    for number, value in enumerate(values):
        assert result.add(row(str(number), value))
    assert result.render()[0] is None


def test_count_share_uses_all_filtered_rows_and_having_is_post_count():
    result = accumulator(operation="row_count", column_ids=[], share_of_total=True,
                         having=[dict(operator="greater_than", value=1)], limit=1)
    for group in ["a", "b", "a", "a"]:
        assert result.add(row(group, 100))
    text, _ = result.render()
    assert "행 개수 3건" in text and "분자 3 / 분모 4" in text and "비중 약 75%" in text


def test_percent_having_converts_stored_ratio_only_with_confirmed_unit():
    result = accumulator(having=[condition(50, value_unit="percent")])
    assert result.add(row("a", 0.6, number_formats={"B": "0%"}))
    assert '"a"' in result.render()[0]
    unsafe = accumulator(having=[condition(50, value_unit="percent")])
    assert unsafe.add(row("a", 0.6))
    assert unsafe.render()[0] is None


@pytest.mark.parametrize("changes", [
    {"share_of_total": True, "statistic": "average"},
    {"share_of_total": True, "column_ids": ["B", "C"]},
    {"having": [condition(1)], "statistic": "all"},
    {"having": [condition(1, target="share", value_unit="percent")]},
    {"having": [dict(column_id="C", operator="greater_than", value=1)]},
    {"per_group_limit": 1},
])
def test_unsupported_combinations_fail_before_any_answer(changes):
    result = accumulator(**changes)
    assert not result.add(row("a", 1)) and result.render()[0] is None


def test_having_blank_group_never_silently_drops_unknown_aggregate():
    result = accumulator(having=[condition(1)])
    assert result.add(row("blank", None)) and result.add(row("known", 100))
    assert result.render()[0] is None


def test_having_no_match_reports_zero_groups_without_fabrication():
    result = accumulator(having=[condition(100)], order_by="B", limit=1)
    assert result.add(row("a", 1))
    text, _ = result.render()
    assert "그룹은 0개" in text and '"a"' not in text


@pytest.mark.parametrize("operator,count", [("equals", 1), ("not_equals", 2),
    ("greater_than", 1), ("greater_than_or_equal", 2), ("less_than", 1), ("less_than_or_equal", 2)])
def test_every_having_comparison_has_exact_inclusive_boundary(operator, count):
    result = accumulator(having=[condition(2, operator)])
    for name, amount in [("one", 1), ("two", 2), ("three", 3)]:
        assert result.add(row(name, amount))
    assert f"그룹은 {count}개" in result.render()[0]


def test_extreme_scale_share_denominator_preserves_every_positive_group():
    from app.agent.query.grouped_aggregate_postprocess import AggregatePostprocess
    result = accumulator(share_of_total=True)
    assert result.add(row("huge", 10 ** 100)) and result.add(row("tiny", 1e-100))
    postprocess = AggregatePostprocess(result.state)
    groups = list(result.state.groups.values())
    assert postprocess.select(groups) == groups
    assert postprocess.denominator == result.state.units["B"].total
    assert postprocess.shares[id(groups[0])] < 100
    assert postprocess.shares[id(groups[1])] > 0


@pytest.mark.parametrize("operator,count", [("equals", 0), ("greater_than_or_equal", 0), ("less_than", 2)])
def test_extreme_scale_share_having_uses_exact_total_and_cross_products(operator, count):
    result = accumulator(share_of_total=True, having=[dict(target="share", operator=operator,
                         value=100, value_unit="percent")])
    assert result.add(row("huge", 10 ** 100)) and result.add(row("tiny", 1e-100))
    assert f"그룹은 {count}개" in result.render()[0]
