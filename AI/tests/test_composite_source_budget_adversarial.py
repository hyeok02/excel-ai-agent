"""Independent subquestions share the same request-local source read budget."""
import pytest

from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.large_workbook_fixtures import parsed, tiny_caps, workbook
from tests.support.replanning_adversarial import Planner, offline, run
from tests.support.structured_adversarial import compound, plan


@pytest.mark.parametrize("limits", [SourceReadLimits(max_cells=60), SourceReadLimits(max_reads=1)])
def test_later_question_cannot_reset_exhausted_source_budget(tiny_caps, limits):
    matrix = [["Record", "Region", "Status", "Amount", "Costs"],
              *[[f"Item{n}", "North", "Open", n, n * 10] for n in range(1, 10)]]
    summary, index, _ = parsed(workbook({"Records": matrix}), limits=limits)
    texts = ["Records 시트 Amount 합계", "Records 시트 Amount 평균"]
    planner = Planner(compound(texts, [plan(summary), plan(summary, statistic="average")]), None)
    answer = run("; ".join(texts), summary, index, planner)
    assert answer.status == "limited", answer.model_dump()
    assert answer.verification.level == "source_checked", answer.model_dump()
    assert "합계 45" in answer.answer and "평균 5 " not in answer.answer
    assert "compound_request_coverage" not in answer.verification.checks
    assert all(item.label.startswith("문항 1 · ") for item in answer.evidence)
    assert planner.repairs == []
