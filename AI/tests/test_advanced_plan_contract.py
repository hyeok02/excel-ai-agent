"""Malformed advanced fields must not silently become an ordinary query."""
import pytest
from pydantic import ValidationError

from app.agent.query.tabular_query_models import TabularAggregateCondition
from tests.test_partitioned_ranked_rows import accumulator, row


@pytest.mark.parametrize("value", [True, False, "10", None, float("inf"), float("nan"), 10 ** 400])
def test_having_threshold_requires_finite_numeric_value(value):
    with pytest.raises(ValidationError):
        TabularAggregateCondition(operator="greater_than", value=value)


@pytest.mark.parametrize("changes", [
    {"group_by": []}, {"group_by": ["C", "C"]}, {"group_by": ["X"]},
    {"column_ids": ["X"]}, {"column_ids": []}, {"order_by": None}, {"order_by": "C"},
    {"limit": 1}, {"per_group_limit": None}, {"share_of_total": True},
    {"identity_column_ids": ["A", "A"]}, {"identity_column_ids": ["C"]},
    {"identity_column_ids": ["B"]},
    {"having": [{"column_id": "B", "operator": "greater_than", "value": 1}]},
])
def test_invalid_partition_contract_fails_before_returning_rows(changes):
    result = accumulator(**changes)
    assert not result.add(row(1, 10))
    assert result.render() == (None, [])
