import re

FIELD_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("headcount", ("인원", "직원수", "headcount", "employee", "fte")),
    ("profit_margin", ("이익률", "수익률", "profit margin", "margin")),
    ("revenue", ("매출", "매출액", "revenue", "sales", "turnover")),
    ("cost", ("비용", "원가", "경비", "인건비", "cost", "expense")),
    ("profit", ("영업이익", "순이익", "이익", "profit", "income")),
    ("period", ("날짜", "일자", "연도", "분기", "월", "date", "year", "quarter", "month")),
    ("rate", ("비율", "증감률", "달성률", "rate", "ratio", "percentage")),
    ("quantity", ("수량", "판매량", "건수", "개수", "quantity", "count", "units sold")),
    ("category", ("구분", "분류", "유형", "부서", "지역", "category", "type", "department", "region")),
    ("amount", ("금액", "합계", "총액", "amount", "total", "value")),
)


def classify_standard_field(
    labels: list[str],
    data_type: str,
) -> tuple[str, float, list[str]]:
    normalized = _normalized(labels)
    for field, markers in FIELD_MARKERS:
        marker = next((item for item in markers if item in normalized), None)
        if marker:
            return field, 0.92, [f"헤더 의미어 '{marker}' 일치"]
    if data_type == "date":
        return "period", 0.8, ["열 데이터형이 날짜"]
    if data_type == "text":
        return "category", 0.62, ["반복 가능한 텍스트 차원"]
    if data_type == "number":
        return "metric", 0.55, ["숫자형 측정값"]
    return "unknown", 0.4, ["표준 필드 후보를 확정할 근거 부족"]


def _normalized(labels: list[str]) -> str:
    value = " ".join(labels).lower()
    return re.sub(r"[_\-/.]+", " ", value)
