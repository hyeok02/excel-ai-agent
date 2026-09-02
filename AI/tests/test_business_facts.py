from app.services.insights.business_facts import build_business_facts


def _cell(address: str, value: object) -> dict[str, object]:
    return {
        "address": address,
        "value": value,
        "formula": None,
        "cached_value": None,
        "number_format": "General",
    }


def test_extracts_focus_entity_and_numeric_change() -> None:
    regions = [
        {
            "title": "분석 설정",
            "semantic": {"role": "description"},
            "preview_rows": [
                [_cell("A1", "Focus Co."), _cell("B1", "Riot Games, Inc.")]
            ],
        },
        {
            "title": "인원 추이",
            "semantic": {"role": "data"},
            "preview_rows": [
                [_cell("A2", "2023-09-01T00:00:00"), _cell("B2", 6101)],
                [_cell("A3", "2025-06-01T00:00:00"), _cell("B3", 5417)],
            ],
        },
    ]
    schemas = [
        {"column": "A", "display_name": "Date", "source_range": "A2:B3"},
        {
            "column": "B",
            "display_name": "Total Employees",
            "source_range": "A2:B3",
        },
    ]

    result = build_business_facts("인력", regions, schemas, max_records=3)

    assert result["selected_records"][0]["location"] == "인력!A1:B1"
    assert result["numeric_changes"] == [
        {
            "metric": "Total Employees",
            "earliest_period": "2023-09-01T00:00:00",
            "earliest_value": 6101.0,
            "latest_period": "2025-06-01T00:00:00",
            "latest_value": 5417.0,
            "change": -684.0,
            "change_rate_percent": -11.21,
            "evidence": ["인력!A2:B2", "인력!A3:B3"],
        }
    ]


def test_excludes_pending_formula_noise_and_long_values() -> None:
    regions = [
        {
            "title": "결과",
            "semantic": {"role": "output"},
            "preview_rows": [
                [
                    _cell("A1", "#PEND"),
                    _cell("B1", "x" * 241),
                    _cell("C1", 5411),
                ]
            ],
        }
    ]

    result = build_business_facts("결과", regions, [], max_records=2)

    values = result["selected_records"][0]["values"]
    assert values == [
        {
            "cell": "C1",
            "label": None,
            "value": 5411,
            "number_format": "General",
        }
    ]


def test_excludes_header_and_internal_code_rows() -> None:
    regions = [
        {
            "title": "기업 현황",
            "semantic": {"role": "data"},
            "preview_rows": [
                [_cell("A1", "Company Name"), _cell("B1", "Headcount Latest")],
                [_cell("A2", "SP_COMPANY_NAME"), _cell("B2", "SP_HEADCOUNT")],
                [_cell("A3", "Riot Games, Inc."), _cell("B3", 5411)],
            ],
        }
    ]

    result = build_business_facts("기업", regions, [], max_records=3)

    assert result["selected_records"] == [
        {
            "location": "기업!A3:B3",
            "region": "기업 현황",
            "values": [
                {
                    "cell": "A3",
                    "label": "Company Name",
                    "value": "Riot Games, Inc.",
                    "number_format": "General",
                },
                {
                    "cell": "B3",
                    "label": "Headcount Latest",
                    "value": 5411,
                    "number_format": "General",
                },
            ],
        }
    ]


def test_finds_identity_row_without_workbook_specific_headers() -> None:
    """'Focus Co.' 같은 특정 문구가 없어도 이름표-값 행을 찾아야 한다."""
    regions = [
        {
            "title": "설비 개요",
            "semantic": {"role": "description"},
            "preview_rows": [
                [_cell("A1", "설비 라인"), _cell("B1", "2공장 압출 라인")]
            ],
        }
    ]

    result = build_business_facts("설비", regions, [], max_records=1)

    assert result["selected_records"][0]["location"] == "설비!A1:B1"
