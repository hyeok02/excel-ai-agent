"""한 항목의 한 값을 코드가 직접 짚는지."""
from app.agent.tools.workbook_cell_lookups import build_cell_lookup
from app.agent.tools.workbook_headers import build_header_context
from tests.support.checklist_rows import SHEET, built, row


def _looked_up(question: str):
    return built(build_cell_lookup, question)


def test_reads_one_cell_when_the_question_names_one_row() -> None:
    found = _looked_up("CVD #2 IP가 뭐야?")

    assert found["label"] == "CVD #2"
    assert found["header"] == "IP"
    assert found["value"] == "10.1.7.7"
    assert found["value_reference"] == f"{SHEET}!C7"


def test_does_not_confuse_rows_that_share_a_word() -> None:
    # 'CVD'는 모든 행이 함께 쓴다. 한 행에만 있는 낱말로 가리켰을 때만 짚는다.
    assert _looked_up("CVD IP가 뭐야?") is None


def test_does_not_read_a_cell_without_a_named_row() -> None:
    assert _looked_up("IP가 뭐야?") is None


def test_reads_one_cell_when_the_row_name_carries_a_particle() -> None:
    # 'CVD #2의'는 'CVD #2'를 가리킨다. 조사가 붙은 채로는 표의 이름과 맞지
    # 않아 답을 못 냈다.
    found = _looked_up("CVD #2의 IP가 뭐야?")

    assert found["label"] == "CVD #2"
    assert found["value_reference"] == f"{SHEET}!C7"


def test_uses_an_explicit_code_instead_of_the_nearest_text_label() -> None:
    source = [
        row(5, {"A": "설비코드", "B": "점검항목", "C": "측정값", "D": "기준값"}),
        row(6, {"A": "EX-101", "B": "진동", "C": 3.2, "D": 5.0}),
        row(7, {"A": "EX-102", "B": "베어링 온도", "C": 68.4, "D": 80.0}),
    ]
    headers = build_header_context(tuple(source), source)

    found = build_cell_lookup(source, headers, "EX-102의 측정값은?")

    assert found["label"] == "EX-102"
    assert found["header"] == "측정값"
    assert found["value"] == 68.4


def test_conflicting_names_from_two_label_columns_are_not_guessed() -> None:
    source = [
        row(5, {"A": "설비코드", "B": "점검항목", "C": "측정값"}),
        row(6, {"A": "EX-101", "B": "진동", "C": 3.2}),
        row(7, {"A": "EX-102", "B": "온도", "C": 68.4}),
    ]
    headers = build_header_context(tuple(source), source)

    assert build_cell_lookup(source, headers, "EX-102 진동 측정값은?") is None
