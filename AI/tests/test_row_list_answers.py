"""조건에 맞는 행을 코드가 직접 골라 나열하는지."""
from app.agent.tools.workbook_row_counts import build_row_count
from app.agent.tools.workbook_row_lists import build_row_list
from tests.support.checklist_rows import MARKS, SHEET, built


def _built(question: str):
    return built(build_row_list, question)


def _counted(question: str):
    return built(build_row_count, question)


def test_lists_the_rows_marked_negative() -> None:
    found = _built("네트워크가 불안정한 장비는?")

    assert found["header"] == "네트워크 안정"
    assert found["label_header"] == "장비"
    assert found["polarity"] == "negative"
    assert [item["label"] for item in found["matches"]] == ["CVD #1", "CVD #2", "CVD #4"]
    assert found["blank_count"] == 1


def test_lists_the_rows_marked_positive() -> None:
    # '안정된'의 '안'이 부정으로 읽히면 안 된다. 머리글에 쓰인 말을 걷어낸
    # 나머지에서만 긍정·부정을 읽는다.
    found = _built("네트워크 안정된 장비는?")

    assert found["polarity"] == "positive"
    assert [item["label"] for item in found["matches"]] == ["CVD #3", "CVD #5"]


def test_cites_both_the_name_and_the_mark_of_every_listed_row() -> None:
    found = _built("네트워크가 불안정한 장비는?")

    for item in found["matches"]:
        assert item["label_reference"].startswith(f"{SHEET}!D")
        assert item["value_reference"].startswith(f"{SHEET}!F")


def test_ignores_a_question_without_a_clear_condition() -> None:
    assert _built("장비가 총 몇 대야?") is None
    assert _built("네트워크 안정 상태를 알려줘") is None


def test_counts_the_named_column() -> None:
    found = _counted("장비가 총 몇 대야?")

    assert found["header"] == "장비"
    assert found["count"] == len(MARKS)
    assert found["header_reference"] == f"{SHEET}!D5"


def test_does_not_count_a_column_the_question_never_names() -> None:
    # '몇'만 보고 아무 열이나 세면 엉뚱한 수가 근거 확인 딱지를 달고 나간다.
    assert _counted("몇 개야?") is None
    assert _counted("상태가 몇 개야?") is None


def test_counts_the_column_the_question_names_even_if_it_is_not_the_nearest() -> None:
    # 표시 열 왼쪽의 가장 가까운 글자 열만 세면, 질문이 부른 열이 무시된다.
    found = _counted("IP가 몇 개야?")

    assert found["header"] == "IP"
    assert found["count"] == len(MARKS)


def test_ignores_a_question_that_is_not_about_counting() -> None:
    assert _counted("네트워크가 불안정한 장비는?") is None


def test_lists_the_rows_when_the_question_names_the_mark() -> None:
    # 표에 적힌 x·o를 질문에 그대로 쓰는 사람이 많다. 어간만 보면 아무 극성도
    # 읽히지 않아 목록이 꺼지고 모델 추측이 나갔다.
    negative = _built("네트워크 안정이 x인 장비는?")
    positive = _built("네트워크 안정이 o인 장비 알려줘")

    assert [item["label"] for item in negative["matches"]] == [
        "CVD #1", "CVD #2", "CVD #4",
    ]
    assert [item["label"] for item in positive["matches"]] == ["CVD #3", "CVD #5"]


def test_does_not_read_an_english_word_as_a_mark() -> None:
    # 'ok'나 'vs'의 첫 글자를 표시로 읽으면 조건 없는 질문에 목록이 나간다.
    assert _built("네트워크 안정 ok야?") is None
    assert _built("네트워크 안정 vs 다른 항목") is None


def test_lists_by_the_name_column_the_question_asks_for() -> None:
    # 표시 열 왼쪽의 가장 가까운 글자 열만 쓰면, 질문이 '장비'를 물어도 그 옆
    # 'IP' 열이 나열될 수 있다.
    found = _built("TCK 작업이 o인 장비는?")

    assert found["label_header"] == "장비"
    assert [item["label"] for item in found["matches"]][:2] == ["CVD #1", "CVD #2"]
