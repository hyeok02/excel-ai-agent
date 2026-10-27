"""A source literal or display continuation is not an independent calculation."""
from types import SimpleNamespace

import pytest

from app.agent.query.composite_split import split_compound_question
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex


def sources(*values):
    cells = tuple(IndexedCell("Records", f"A{position}", value, None)
                  for position, value in enumerate(values, 1))
    index = WorkbookDataIndex("sample.xlsx", (IndexedRow("Records", 1, cells),), len(cells), False)
    return SimpleNamespace(index=index, original_index=index)


@pytest.mark.parametrize("question", [
    "총부채(Total Debt)는 얼마야? 단위도 알려줘.",
    "Operating Income은 2023년에서 2024년으로 얼마나 증가했어? 금액과 증가율을 알려줘.",
    "이 파일은 무엇을 비교하고 있어?",
    "매출을 계산하고 싶어",
    "Status가 ?인 행 수", "Status가 ? 인 행 수",
])
def test_display_continuations_aspect_and_category_suffixes_are_single_requests(question):
    assert split_compound_question(question) is None


def test_question_mark_filter_does_not_split_a_true_two_part_question():
    question = "Status가 x 또는 o인 행 수; Status가 x 또는 ?인 행 수"
    split = split_compound_question(question)
    assert split.parts == ("Status가 x 또는 o인 행 수", "Status가 x 또는 ?인 행 수")


@pytest.mark.parametrize("literal,question", [
    ("오늘 정리하고 완료", "Task가 오늘 정리하고 완료인 행 수"),
    ("정리; 완료", "Task가 정리; 완료인 행 수"),
    ("Why? Because", "Task가 Why? Because인 행 수"),
])
def test_exact_unquoted_original_cell_values_are_not_split(literal, question):
    assert split_compound_question(question, sources("Task", literal)) is None


def test_source_mask_keeps_real_separator_and_exact_original_parts():
    question = "Task가 오늘 정리하고 완료인 행 수; Amount 평균"
    split = split_compound_question(question, sources("Task", "오늘 정리하고 완료"))
    assert split.parts == ("Task가 오늘 정리하고 완료인 행 수", "Amount 평균")


def test_source_base_verb_cannot_hide_a_legitimate_question_connector():
    split = split_compound_question("Amount 합계를 정리하고, Customer 수를 알려줘", sources("정리"))
    assert split.parts == ("Amount 합계를 정리하고", "Customer 수를 알려줘")


def test_format_continuation_is_not_discarded_from_a_larger_composite():
    question = "Records: Amount 합계는? 단위도 알려줘.; Customer 중복 제외 건수"
    split = split_compound_question(question)
    assert split.shared_prefix == "Records"
    assert split.parts == ("Amount 합계는? 단위도 알려줘.", "Customer 중복 제외 건수")


def test_unrelated_actual_operations_are_not_display_continuations():
    split = split_compound_question("Amount 합계는? 단위별 건수를 알려줘.")
    assert split.parts == ("Amount 합계는?", "단위별 건수를 알려줘.")


def test_ordinary_question_does_not_scan_sources():
    class UnreadableIndex:
        @property
        def rows(self):
            raise AssertionError("ordinary single request must not inspect the index")

    assert split_compound_question("Amount 합계", SimpleNamespace(index=UnreadableIndex())) is None
