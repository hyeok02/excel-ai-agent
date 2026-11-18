"""One named row's change between two dated columns, only when nothing else answered."""
from types import SimpleNamespace

from app.agent.query import member_column_changes as module
from tests.test_column_change_counts import _table
from tests.test_named_series_answers import Names


def _ask(monkeypatch, question, names):
    monkeypatch.setattr(module, "build_query_tables", lambda summary: [_table()])
    return module.member_change_answer(question, object(), SimpleNamespace(rows=()), Names(names))


def test_the_named_row_and_group_change_is_computed_and_its_readings_stated(monkeypatch):
    answer = _ask(monkeypatch, "메인 상업용 전기요금은 작년보다 얼마나 올랐어?", {"상업용": "Commercial", "메인": "Maine"})
    assert answer.answer == ("해석: ‘상업용’ → Commercial, ‘메인’ → Maine\n"
                             "Maine의 Commercial: August 2025 21.5 → August 2026 21, 0.5(2.33%) 내렸습니다.")
    assert answer.status == "limited"
    written = _ask(monkeypatch, "Ohio 가정용 요금은 작년보다 얼마나 변했어?", {"가정용": "Residential"})
    assert written.answer.endswith("Ohio의 Residential: August 2025 20 → August 2026 19, 1(5.00%) 내렸습니다.")


def test_no_single_row_or_group_or_no_comparison_answers_nothing(monkeypatch):
    assert _ask(monkeypatch, "상업용 전기요금은 작년보다 얼마나 올랐어?", {"상업용": "Commercial"}) is None  # no row
    assert _ask(monkeypatch, "메인 전기요금은 작년보다 얼마나 올랐어?", {"메인": "Maine"}) is None  # no group
    assert _ask(monkeypatch, "메인 상업용 전기요금 알려줘", {"상업용": "Commercial", "메인": "Maine"}) is None
    assert _ask(monkeypatch, "상업용 전기요금이 작년보다 오른 주는 몇 개야?", {"상업용": "Commercial"}) is None  # a count


def test_a_phrase_naming_the_group_does_not_take_the_row_word_with_it(monkeypatch):
    names = {"뉴욕 가정용": "Residential", "가정용": "Residential", "메인": "Maine"}
    answer = _ask(monkeypatch, "메인 가정용 요금은 작년보다 얼마나 올랐어?", {**names, "메인 가정용": "Residential"})
    assert answer.answer.endswith("Maine의 Residential: August 2025 28 → August 2026 32, 4(14.29%) 올랐습니다.")


def test_two_named_rows_are_compared_on_the_newest_column(monkeypatch):
    names = {"상업용": "Commercial", "메인": "Maine", "버몬트": "Vermont"}
    answer = _ask(monkeypatch, "메인과 버몬트 상업용 전기요금 차이는?", names)
    assert answer.answer.endswith("Commercial · August 2026: Maine 21, Vermont 19. Maine가 Vermont보다 2 높습니다.")
    assert _ask(monkeypatch, "메인 상업용 전기요금 차이는?", names) is None  # one row is no comparison
