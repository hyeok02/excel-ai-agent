from app.services.insights.facts.business_facts import build_business_facts
from app.services.insights.narratives.narrative_values import identity


def _row(row: int, cells: list[str]) -> list[dict[str, object]]:
    return [
        {"address": f"{chr(66 + index)}{row}", "value": value}
        for index, value in enumerate(cells)
    ]


def _regions() -> list[dict[str, object]]:
    """
    설정 행이 앞자리를 차지하고 대상 행이 뒤에 오는 배치.

    S&P 템플릿의 보조 시트가 실제로 이렇게 생겼다. 모양만 식별 행 같은 설정 행에
    밀리면 기록 수 상한이 작을 때 대상 이름을 찾지 못한다.
    """
    return [{"title": "Settings", "preview_rows": [
        _row(5, ["Magnitude", "1e-06"]),
        _row(6, ["Standard", "1e-06"]),
        _row(7, ["Millions", "1e-06"]),
        _row(8, ["Billions", "1e-09"]),
        _row(9, ["Trillions", "1e-12"]),
        _row(10, ["Entity Name", "SP_ENTITY_NAME", "Walmart Inc."]),
    ]}]


def _identity_for(max_records: int) -> str:
    facts = build_business_facts("Intermediate", _regions(), [], max_records)
    name, _ = identity({"business_facts": facts})
    return name


def test_subject_row_survives_a_small_record_limit() -> None:
    assert _identity_for(2) == "Walmart Inc."


def test_subject_is_found_at_every_record_limit() -> None:
    assert {_identity_for(limit) for limit in (2, 4, 6, 12)} == {"Walmart Inc."}
