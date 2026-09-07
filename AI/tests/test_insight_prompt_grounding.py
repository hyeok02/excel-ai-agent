from app.services.insights.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    build_user_prompt_from_context,
)
from app.services.workbook_parser import WorkbookSummary


def test_prompt_has_no_canned_subject_numbers_or_corporate_framing() -> None:
    summary = WorkbookSummary(filename="학교급식표.xlsx", sheet_count=0, sheets=[])

    prompt = f"{SYSTEM_PROMPT}\n{build_user_prompt(summary)}"

    for foreign_example in ("Riot", "6,101", "5,417", "684", "동종기업", "대상 기업"):
        assert foreign_example not in prompt
    assert "원문 표기를 그대로" in prompt
    assert "insights를 빈 배열" in prompt
    assert "현재 요청의 workbook_metadata" in prompt


def test_prompt_keeps_actual_text_values_without_replacing_the_domain() -> None:
    context = {
        "filename": "급식.xlsx",
        "sheets": [{
            "name": "식단",
            "business_facts": {
                "selected_records": [{
                    "location": "식단!A1:B1",
                    "values": [
                        {"cell": "A1", "value": "중식"},
                        {"cell": "B1", "value": "현미밥, 미역국"},
                    ],
                }],
                "numeric_changes": [],
            },
        }],
    }

    prompt = build_user_prompt_from_context(context, 5)

    assert "현미밥, 미역국" in prompt
    assert "중식" in prompt
    assert "직원" not in prompt
    assert "기간별 증감·비교는 이 파일에 해당 근거가 있을 때만" in prompt
