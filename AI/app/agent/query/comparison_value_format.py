"""원본 Excel 표시 형식을 보존해 비교 값과 증감을 표시한다."""

import re

from app.agent.query.excel_number_formats import (
    delta_format,
    display_value,
    number_text,
    parse_number_format,
    scaled_value,
)

_PEOPLE_COUNT = re.compile(
    r"인원(?!\s*(?:당|별|비율|율|구성|비용))|직원\s*수|(?:전체|총)\s*직원"
    r"|(?<![a-z])headcount(?![a-z])|(?<![a-z])employees(?![a-z])"
    r"|(?<![a-z])(?:number\s+of\s+(?:employees|staff)|(?:employee|staff)\s+count)(?![a-z])",
    re.I,
)
_COUNTED_AS_PEOPLE = re.compile(
    r"(?:몇|약|총|\d[\d,.]*)\s*명|(?<![가-힣a-z])명(?=\s|$|[?.,]|이|은|을|으로|씩|당)",
    re.I,
)


def comparison_values(
    start: object,
    end: object,
    change: object,
    start_format: object = None,
    end_format: object = None,
    fallback_unit: str = "",
) -> tuple[str, str, str]:
    """시작·종료·절대 증감 값을 같은 열의 표시 의미로 렌더링한다."""
    before = parse_number_format(start_format)
    after = parse_number_format(end_format)
    start_text = display_value(start, before, fallback_unit)
    end_text = display_value(end, after, fallback_unit)
    if before.percent and after.percent:
        moved_value = abs(scaled_value(end, after) - scaled_value(start, before))
        moved = number_text(moved_value, after) + "%p"
    else:
        moved = display_value(
            abs(float(change)), delta_format(before, after), fallback_unit
        )
    return start_text, end_text, moved


def people_unit(question: str, header: object) -> str:
    """직원 관련 비용·비율·만족도를 사람 수로 오인하지 않는다."""
    asked = f"{question} {header}".casefold()
    return "명" if _PEOPLE_COUNT.search(asked) or _COUNTED_AS_PEOPLE.search(asked) else ""


def percentage_formats(start_format: object, end_format: object) -> bool:
    return (
        parse_number_format(start_format).percent
        and parse_number_format(end_format).percent
    )
