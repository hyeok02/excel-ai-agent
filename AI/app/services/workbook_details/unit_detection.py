from datetime import date, datetime
import re

from openpyxl.styles.numbers import is_date_format

CURRENCY_MARKERS = {
    "₩": "KRW",
    "krw": "KRW",
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "jpy": "JPY",
}


def infer_data_type(values: list[object], number_formats: list[str]) -> str:
    kinds = {_value_kind(value) for value in values if value is not None}
    if any(is_date_format(item) for item in number_formats if item):
        kinds.discard("number")
        kinds.add("date")
    if not kinds:
        return "empty"
    return next(iter(kinds)) if len(kinds) == 1 else "mixed"


def infer_unit(
    labels: list[str],
    values: list[object],
    number_formats: list[str],
    standard_field: str,
) -> tuple[str, str | None, float, list[str]]:
    header = " ".join(labels).lower()
    formats = " ".join(number_formats).lower()
    if _contains_date(header, values, number_formats):
        return "date", "날짜", 0.96, ["날짜 값 또는 날짜 표시 형식"]
    if "%" in formats or _matches(header, ("비율", "증감률", "이익률", "rate", "ratio", "margin")):
        return "percentage", "%", 0.94, ["백분율 표시 형식 또는 비율 헤더"]
    currency = _currency_label(header, formats)
    if currency:
        return "currency", currency, 0.94, ["통화 기호·통화 코드 또는 금액 단위"]
    if _matches(header, ("인원", "인원수", "직원수", "headcount", "employee", "fte")):
        return "headcount", "명", 0.92, ["인원 의미 헤더"]
    if _matches(header, ("수량", "판매량", "건수", "개수", "quantity", "count", "units sold")):
        return "quantity", _quantity_label(header), 0.88, ["수량 의미 헤더"]
    if standard_field in {"revenue", "cost", "profit", "amount"}:
        return "currency", "금액", 0.72, ["금액 성격의 표준 필드"]
    return "none", None, 0.5, ["명시적인 단위 없음"]


def _value_kind(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return "date"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "text"


def _contains_date(header: str, values: list[object], formats: list[str]) -> bool:
    return (
        any(isinstance(value, (date, datetime)) for value in values)
        or any(is_date_format(item) for item in formats if item)
        or _matches(header, ("날짜", "일자", "기준일", "date", "month", "quarter", "year"))
    )


def _currency_label(header: str, formats: str) -> str | None:
    combined = f"{header} {formats}"
    scale_match = re.search(r"(백만원|천만원|억원|천원)", combined)
    if scale_match:
        return scale_match.group(1)
    for marker, label in CURRENCY_MARKERS.items():
        if marker in combined:
            return label
    if re.search(r"(?:^|[^가-힣])원(?:$|[^가-힣])", combined):
        return "KRW"
    return None


def _quantity_label(header: str) -> str:
    if "건" in header or "count" in header:
        return "건"
    return "개"


def _matches(value: str, markers: tuple[str, ...]) -> bool:
    return any(marker in value for marker in markers)
