"""A draft saying the question cannot be answered is not shown as its interpretation."""
from app.agent.query.grounded_interpretation import interpreted_answer
from tests.test_grounded_interpretation import CELLS, _draft, _execution


def test_a_sentence_saying_the_asked_thing_is_unknown_is_no_interpretation():
    unknown = interpreted_answer("동부 매장 수는?", _draft("동부 매장 수는 원본에서 직접 확인할 수 없습니다.", CELLS), _execution())
    assert unknown is None  # nothing answered: the later stages still run
    related = interpreted_answer("동부 매장 수는?", _draft(
        "동부 매장 수는 원본에서 확인할 수 없습니다. 쿠키는 동부 $10,683.50입니다.", CELLS), _execution())
    assert related.answer.endswith("해석: 쿠키는 동부 $10,683.50입니다.")
    assert "question_unanswered" in related.verification.checks
    plain = interpreted_answer("동부가 많은 이유는?", _draft("쿠키는 동부 $10,683.50입니다.", CELLS), _execution())
    assert "question_unanswered" not in plain.verification.checks


def test_a_follow_up_scoped_to_one_range_is_not_answered_from_another():
    draft = _draft("쿠키에서 동부가 $10,683.50로 서부 $6,528.91보다 많기 때문입니다.", CELLS)
    elsewhere = interpreted_answer("'RegPct'!A1:C10 범위의 B열 기준으로: 동부가 많은 이유는?", draft, _execution())
    assert elsewhere is None
    inside = interpreted_answer("'CatReg'!A1:C10 범위의 B열 기준으로: 동부가 많은 이유는?", draft, _execution())
    assert inside is not None and "CatReg — Cookies · East" in inside.answer
