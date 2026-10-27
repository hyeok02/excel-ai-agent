"""NOT cannot transform Excel errors or invalid numeric observations into matches."""
import pytest

from app.agent.query.intent_models import QuestionIntent
from tests.support.large_workbook_fixtures import parsed, tiny_caps, workbook
from tests.support.replanning_adversarial import Planner, offline, rejected, run


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("error", [
    "#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A", "#SPILL!", "#CALC!",
])
def test_not_text_predicate_does_not_turn_original_excel_error_into_valid_row(request, streamed, error):
    if streamed:
        request.getfixturevalue("tiny_caps")
    matrix = [["Record", "Status", "Amount"],
              *[[f"Known{n}", "Open", n] for n in range(1, 9)], ["Bad", error, 999]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    planner = Planner(QuestionIntent(False, "aggregation"), None)
    answer = run("NOT Status = 'Closed' Amount 합계", summary, index, planner)
    rejected(answer)
    assert "합계 1035" not in answer.answer
    assert planner.repairs == []


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("unknown", ["not recorded", "20", True])
def test_not_numeric_equality_does_not_count_invalid_numeric_value(request, streamed, unknown):
    if streamed:
        request.getfixturevalue("tiny_caps")
    matrix = [["Record", "Amount"], *[[f"Known{n}", n] for n in range(1, 9)], ["Bad", unknown]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    planner = Planner(QuestionIntent(False, "row_count"), None)
    rejected(run("NOT (Amount = 20) 행 수", summary, index, planner))
    assert planner.repairs == []


@pytest.mark.parametrize("condition,total", [
    ("NOT Status = 'Closed'", 50), ("NOT (Amount = 20)", 50),
])
def test_known_text_and_numeric_negations_still_compute_normally(condition, total):
    summary, index, _ = parsed(workbook({"Records": [
        ["Record", "Status", "Amount"], ["A", "Open", 10],
        ["B", "Closed", 20], ["C", "Open", 40],
    ]}))
    planner = Planner(QuestionIntent(False, "aggregation"), None)
    answer = run(condition + " Amount 합계", summary, index, planner)
    assert answer.status == "answered" and answer.verification.level == "request_checked", answer.model_dump()
    assert f"합계 {total}" in answer.answer
