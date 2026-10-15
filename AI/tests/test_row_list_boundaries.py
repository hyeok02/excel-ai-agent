from app.agent.tools.workbook_row_lists import build_row_list
from tests.support.checklist_rows import MARKS, built


def test_header_is_not_an_additional_other_mark():
    result = built(build_row_list, "네트워크가 불안정한 장비는?")
    assert len(result["matches"]) + result["other_count"] + result["blank_count"] == len(MARKS)
    assert result["other_count"] == 3


def test_causal_question_does_not_receive_an_unrelated_list_as_its_answer():
    assert built(build_row_list, "왜 네트워크가 불안정한 거야? 구체적인 고장 원인을 알려줘.") is None
