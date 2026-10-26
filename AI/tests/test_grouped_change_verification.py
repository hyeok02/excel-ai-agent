import pytest

from app.agent.query.grouped_change_answers import validated_grouped_change_answer
from tests.support.grouped_change_execution import QUESTION, grouped_execution


@pytest.mark.parametrize("truncated", [False, True])
def test_endpoint_comparison_records_actual_source_checks(truncated):
    answer = validated_grouped_change_answer(QUESTION, grouped_execution(), truncated)
    assert answer is not None
    assert answer.status == ("limited" if truncated else "answered")
    assert answer.verification.level == "source_checked"
    assert answer.verification.checks == ["cited_cells", "source_values"]
    assert "request_alignment" not in answer.verification.checks
    assert bool(answer.limitations) is truncated


def test_wrong_endpoint_values_are_not_given_source_metadata():
    execution = grouped_execution()
    cell = next(item for item in execution.steps[0].result.evidence if item.reference == "B2")
    cell.value = 999
    assert validated_grouped_change_answer(QUESTION, execution, False) is None
