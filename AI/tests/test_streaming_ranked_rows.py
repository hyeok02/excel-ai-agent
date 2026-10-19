"""Ranking never materializes the population or silently omits an unknown key."""
import pytest

from app.agent.query.streaming_ranked_rows import RankedRows
from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow
from app.agent.query.tabular_query_models import TabularQueryPlan


def accumulator(**updates):
    fields = dict(operation="row_list", table_id="Records!A1:B20000", column_ids=["A", "B"],
                  order_by="B", limit=3)
    fields.update(updates)
    plan = TabularQueryPlan(**fields)
    columns = [QueryColumn("A", "Record", "Records!A1", ()),
               QueryColumn("B", "Amount", "Records!B1", ())]
    return RankedRows(plan, columns)


def row(number, value, style="General"):
    return QueryRow(number + 1, {"A": f"Record {number}", "B": value}, number_formats={"B": style})


@pytest.mark.parametrize("descending", [True, False])
def test_exact_top_and_bottom_retain_only_requested_bound_plus_boundary(descending):
    result = accumulator(descending=descending)
    for number in range(1, 20_001):
        assert result.add(row(number, number - 10_000))
        assert len(result.heap) <= 4
    text, limitations = result.render()
    expected = [20_000, 19_999, 19_998] if descending else [1, 2, 3]
    assert [line.split(";")[0] for line in text.splitlines()] == [f"Record: Record {n}" for n in expected]
    assert result.count == 20_000 and not limitations


def test_equal_boundary_uses_stable_source_order_and_reports_exact_n_policy():
    result = accumulator(limit=2)
    for number, value in enumerate([3, 3, 3, 4], 1):
        assert result.add(row(number, value))
    text, limitations = result.render()
    assert text.splitlines()[:2] == ["Record: Record 4; Amount: 4", "Record: Record 1; Amount: 3"]
    assert "경계값이 같은 행" in text and "2개 행" in text
    assert not limitations


def test_explicit_limit_can_render_one_hundred_not_silently_fifty():
    result = accumulator(limit=100)
    for number in range(120):
        assert result.add(row(number, number))
    text, limitations = result.render()
    assert len(text.splitlines()) == 100 and not limitations
    assert len(result.heap) == 101 and "Record: Record 20;" in text


def test_unbounded_sort_is_explicitly_display_limited_after_full_population():
    result = accumulator(limit=None)
    for number in range(60):
        assert result.add(row(number, number))
    text, limitations = result.render()
    assert len(text.splitlines()) == 50
    assert limitations and "60개 행" in limitations[0] and "50개 행" in limitations[0]
    assert len(result.heap) == 51


@pytest.mark.parametrize("value", [None, "", "unknown", True, float("nan"), float("inf")])
def test_unknown_sort_value_fails_even_after_top_rows_are_known(value):
    result = accumulator(limit=1)
    assert result.add(row(1, 1_000_000))
    assert not result.add(row(2, value))


@pytest.mark.parametrize("style", ["0%", "$0.00", "yyyy-mm-dd", "# ?/?"])
def test_unknown_or_mixed_sort_units_fail_even_for_a_nonwinning_row(style):
    result = accumulator(limit=1)
    assert result.add(row(1, 1_000_000))
    assert not result.add(row(2, 1, style))


def test_compatible_decimal_format_differences_do_not_change_rank():
    result = accumulator(limit=1)
    assert result.add(row(1, 10, "0.00"))
    assert result.add(row(2, 11, "0"))
    assert result.render()[0] == "Record: Record 2; Amount: 11"


def test_bottom_sort_does_not_round_large_integer_keys():
    result = accumulator(limit=1, descending=False)
    assert result.add(row(1, 10 ** 35 + 2))
    assert result.add(row(2, 10 ** 35 + 1))
    assert "Record: Record 2;" in result.render()[0]


def test_retained_text_budget_fails_closed(monkeypatch):
    monkeypatch.setattr("app.agent.query.streaming_ranked_rows.MAX_RANKED_CHARACTERS", 10)
    assert not accumulator(limit=1).add(QueryRow(2, {"A": "x" * 11, "B": 5}))
