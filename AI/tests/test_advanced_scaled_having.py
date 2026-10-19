"""Known source magnitudes permit correct HAVING, not only rejection of wrong plans."""
import pytest

from tests.support.advanced_qna_fixtures import checked, condition, group_plan, source
from tests.support.large_workbook_fixtures import ask, offline, tiny_caps


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("unit,large,small,threshold", [
    ("백만원", 120, 80, 100), ("천원", 120_000, 80_000, 100_000),
    ("원", 120_000_000, 80_000_000, 100_000_000),
])
def test_having_converts_physical_quantity_to_source_units(unit, large, small, threshold, streamed, request):
    if streamed:
        request.getfixturevalue("tiny_caps")
    summary, index, _ = source([["Record", f"Amount ({unit})", "Department"],
                               ["First", large, "Alpha"], ["Second", small, "Beta"],
                               ["Third", 0, "Beta"], ["Last", 0, "Beta"]])
    answer = ask("Records 시트 Department별 Amount 합계가 1억원 초과인 그룹 보여줘", summary, index,
                 group_plan(summary, having=[condition(threshold)]))
    checked(answer, scan=streamed)
    assert 'Department: "Alpha"' in answer.answer
    assert 'Department: "Beta"' not in answer.answer
