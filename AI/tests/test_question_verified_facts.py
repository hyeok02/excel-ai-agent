from types import SimpleNamespace

from app.agent.query import verified_facts


def test_comparable_fact_exposes_cited_calculations(monkeypatch) -> None:
    context = {
        "sheets": [
            {
                "name": "거래",
                "business_facts": {
                    "comparable_transactions": {
                        "subject": "MTGE",
                        "subject_cell": "H70",
                        "metrics": [
                            {
                                "kind": "ebitda_multiple",
                                "label": "Enterprise Value / EBITDA",
                                "median": 9.99,
                                "median_cell": "AP66",
                                "subject_value": 5.09,
                                "subject_cell": "AP70",
                                "difference": -4.9,
                                "difference_percent": -49.049,
                            }
                        ],
                    }
                },
            }
        ]
    }
    report = SimpleNamespace(
        overview="MTGE 거래를 비교군과 대조했습니다.",
        insights=[
            SimpleNamespace(
                title="EBITDA 배수는 중앙값보다 낮음",
                fact="MTGE의 EBITDA 배수는 49.0% 낮습니다.",
                evidence=["'거래'!H70", "'거래'!AP70", "'거래'!AP54:AP63", "'거래'!AP66"],
            )
        ],
    )
    monkeypatch.setattr(verified_facts, "_build_context", lambda _: context)
    monkeypatch.setattr(verified_facts, "_source_report", lambda _: report)

    result = verified_facts.build_verified_question_context(SimpleNamespace())

    assert result["insights"][0]["required_references"] == [
        "거래!h70",
        "거래!ap70",
        "거래!ap54:ap63",
        "거래!ap66",
    ]
    assert result["calculations"] == [
        {
            "operation": "difference",
            "operand_references": ["거래!AP66", "거래!AP70"],
            "operand_values": [9.99, 5.09],
            "label": "Enterprise Value / EBITDA",
            "result": -4.9,
            "unit": "multiple",
        },
        {
            "operation": "percent_change",
            "operand_references": ["거래!AP66", "거래!AP70"],
            "operand_values": [9.99, 5.09],
            "label": "Enterprise Value / EBITDA",
            "result": -49.049,
            "unit": "percent",
        },
    ]
    assert result["reference_descriptions"]["거래!AP70"] == (
        "MTGE Enterprise Value / EBITDA"
    )
