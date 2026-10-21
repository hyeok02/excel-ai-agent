"""Combined calculations must follow source structure, not filenames or layout."""
import pytest

from app.agent.query.trend_answers import trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.tabular_query_fixtures import table_fixture


def source(headers, records, order, reverse=False):
    matrix = [[headers[n] for n in order], *[[row[n] for n in order] for row in records]]
    if reverse:
        matrix[1:] = reversed(matrix[1:])
    summary, index = table_fixture([(4, 3, matrix)], sheet_name="Unrelated Source")
    return summary, index


def original_evidence(answer, index):
    cells = {(cell.sheet_name, cell.address): cell.value for row in index.rows for cell in row.cells}
    assert answer.evidence
    for cell in answer.evidence:
        assert cell.value == cells[(cell.sheet_name, cell.reference)], cell


@pytest.mark.parametrize("order,reverse", [((0, 1, 2, 3), False), ((3, 2, 0, 1), True), ((1, 0, 3, 2), False)])
@pytest.mark.parametrize("scale", [1, 7])
def test_scoped_share_is_invariant_to_layout_order_and_scale(order, reverse, scale):
    records = []
    for day, amounts in [("2024-01-31", (20, 30, 50)), ("2024-02-29", (10, 60, 30))]:
        for team, amount in zip(("Orchid", "Cedar", "Willow"), amounts):
            records += [[day, team, amount * scale, "North"], [day, team, 99999, "South"]]
    summary, index = source(["Date", "Team", "Headcount", "Zone"], records, order, reverse)
    answer = trend_answer("North Zone만 Team별 Headcount 비중 추이", summary, index)
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked"
    for text in ("20% → 10%", "30% → 60%", "50% → 30%"):
        assert text in answer.answer, answer.answer
    original_evidence(answer, index)


@pytest.mark.parametrize("order,reverse", [((0, 1, 2, 3), False), ((3, 2, 0, 1), True)])
def test_grouped_growth_uses_its_own_group_even_after_columns_and_rows_move(order, reverse):
    records = [["2023-01-31", "Orchid", 100, "North"], ["2023-01-31", "Cedar", 500, "North"],
               ["2023-02-28", "Orchid", 200, "North"], ["2023-02-28", "Cedar", 300, "North"],
               ["2024-01-31", "Orchid", 110, "North"], ["2024-01-31", "Cedar", 400, "North"],
               ["2024-02-29", "Orchid", 240, "North"], ["2024-02-29", "Cedar", 450, "North"]]
    summary, index = source(["Date", "Team", "Headcount", "Zone"], records, order, reverse)
    answer = trend_answer("2024년 North Zone만 Team별 Headcount 전년 동기 대비 증감률 추이", summary, index)
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked"
    assert "10% → 20%" in answer.answer and "-20% → 50%" in answer.answer
    original_evidence(answer, index)


@pytest.mark.parametrize("tail", ["세금 제외", "달러로 환산", "예측도", "가중평균", "상위 1개"])
def test_composed_growth_never_ignores_an_unbound_extra_operation(tail):
    summary, index = source(["Date", "Team", "Headcount", "Zone"], [
        ["2023", "Orchid", 100, "North"], ["2024", "Orchid", 120, "North"],
        ["2025", "Orchid", 150, "North"]], (0, 1, 2, 3))
    answer = trend_answer(f"Team별 Headcount 증감률 추이 {tail}", summary, index)
    assert answer is not None
    assert answer.status != "answered", answer.model_dump()
    assert answer.verification.level != "request_checked", answer.model_dump()
