"""A sentence giving values for two years must cite a cell for each year."""
from app.agent.query.grounded_interpretation import _years_cited


def test_two_years_read_from_one_cell_are_not_kept():
    sentence = "현재 천식 유병률은 2010년 5.8%에서 2020년 5.8%로 변화가 없습니다."
    assert not _years_cited(sentence, set(), 1)
    assert not _years_cited(sentence, {2020}, 2)
    assert _years_cited(sentence, {2010, 2020}, 2) and _years_cited(sentence, set(), 2)
    assert _years_cited("2020년 값은 5.8%입니다.", set(), 1)
