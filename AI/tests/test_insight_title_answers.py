"""A question naming a verified insight by its full title is answered by that insight."""
from app.agent.query import insight_title_answers
from app.agent.query.insight_title_answers import insight_title_answer
from tests.tabular_query_fixtures import table_fixture

MATRIX = [["Rank", "Holder", "Share (%)"], [1, "Alpha", 50], [2, "Beta", 30], [3, "Gamma", 10]]


def _patched(monkeypatch, evidence=("'Arbitrary'!A1", "'Arbitrary'!C2:C4")):
    monkeypatch.setattr(insight_title_answers, "build_verified_question_context", lambda _summary: {"insights": [
        {"title": "상위 3개 항목의 비중 합계", "fact": "상위 3개 항목의 비중 합계는 90%입니다.",
         "evidence": list(evidence), "confidence": 1.0},
        {"title": "상위 3개", "fact": "짧은 제목", "evidence": ["'Arbitrary'!A1"]}]})
    return table_fixture([(1, 1, MATRIX)])


def test_a_suggested_question_gets_the_insight_fact_with_its_cited_cells(monkeypatch) -> None:
    summary, index = _patched(monkeypatch)
    answer = insight_title_answer("상위 3개 항목의 비중 합계 관련 수치와 원본 근거를 보여줘", summary, index)

    assert answer.answer == "상위 3개 항목의 비중 합계는 90%입니다."
    assert {item.reference for item in answer.evidence} == {"A1", "C2", "C3", "C4"}


def test_an_added_condition_or_a_missing_cell_keeps_the_original_answer(monkeypatch) -> None:
    summary, index = _patched(monkeypatch)
    assert insight_title_answer("2023년 상위 3개 항목의 비중 합계 관련 수치와 원본 근거를 보여줘", summary, index) is None

    summary, index = _patched(monkeypatch, evidence=("'Arbitrary'!Z99",))
    assert insight_title_answer("상위 3개 항목의 비중 합계 관련 수치와 원본 근거를 보여줘", summary, index) is None
