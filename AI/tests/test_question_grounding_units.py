"""Unit translations must be supported by cited source cells."""
from app.agent.query.answer_grounding import answer_is_grounded
from tests.test_question_answer_grounding import _evidence, _execution


def test_cited_currency_and_share_units_allow_their_korean_readings() -> None:
    debt = [
        _evidence("R8", "Unit", "USD millions", "Moved"),
        _evidence("Q42", "Metric", "Total Debt", "Moved"),
        _evidence("R42", "원본 값", 64607, "Moved"),
    ]
    shares = [
        _evidence("F20", "원본 셀", "Shares Held", "Renamed"),
        _evidence("F30", "원본 셀", 123456, "Renamed"),
    ]

    assert answer_is_grounded("총부채는 64,607백만 달러입니다.", debt, _execution())
    assert answer_is_grounded("주식수는 123,456주입니다.", shares, _execution())
    assert not answer_is_grounded("총부채는 64,607유로입니다.", debt, _execution())
