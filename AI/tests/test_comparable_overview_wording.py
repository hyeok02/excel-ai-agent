from app.services.insights.narratives.comparable_narratives import comparable_transaction_report


def _context(peer_count=10, valid_count=3, ebitda_percent=-49.0, kinds=None):
    metrics = {
        "transaction_value": {
            "kind": "transaction_value", "label": "Total Value ($M)",
            "subject_value": 911.8, "median": 1196.6, "difference": -284.8,
            "difference_percent": -23.8, "valid_count": peer_count,
            "peer_count": peer_count, "evidence": ["'Deal Review'!A1:B6"],
        },
        "ebitda_multiple": {
            "kind": "ebitda_multiple", "label": "TV/EBITDA",
            "subject_value": 5.09, "median": 9.99,
            "difference": -4.90 if ebitda_percent < 0 else 4.90,
            "difference_percent": ebitda_percent, "valid_count": valid_count,
            "peer_count": peer_count, "evidence": ["'Deal Review'!A1:B6"],
        },
    }
    selected = kinds or ("transaction_value", "ebitda_multiple")
    return {"sheets": [{"name": "Deal Review", "business_facts": {
        "comparable_transactions": {
            "subject": "Sample Investment Co.",
            "peer_count": peer_count,
            "metrics": [metrics[kind] for kind in selected],
        }
    }}]}


def _overview(**kwargs):
    return comparable_transaction_report(_context(**kwargs))[1]


def test_full_coverage_multiple_is_the_price_conclusion_and_amount_is_size() -> None:
    overview = _overview(valid_count=10)

    assert overview == "EBITDA 대비 인수가격은 비교 거래 중앙값보다 49.0% 낮습니다."
    assert "거래 가격" not in overview and "23.8%" not in overview


def test_opposite_directions_keep_their_own_wording() -> None:
    assert _overview(valid_count=10, ebitda_percent=12.0) == (
        "EBITDA 대비 인수가격은 비교 거래 중앙값보다 12.0% 높습니다."
    )


def test_half_coverage_is_enough_and_less_is_named_as_excluded() -> None:
    assert _overview(valid_count=5).startswith("EBITDA 대비 인수가격은")
    thin = _overview(valid_count=3)
    assert thin.startswith("EBITDA 기준 배수가 10건 중 3건만 값이 있어 가격 수준은 판단할 수 없습니다.")
    assert "거래 규모뿐이며, 비교 거래 중앙값보다 23.8% 작습니다" in thin


def test_a_single_metric_reads_on_its_own() -> None:
    assert _overview(kinds=("transaction_value",)) == (
        "가격 수준을 비교할 배수 열이 없습니다. "
        "비교할 수 있는 것은 거래 규모뿐이며, 비교 거래 중앙값보다 23.8% 작습니다."
    )
    assert _overview(kinds=("ebitda_multiple",), valid_count=10).startswith(
        "EBITDA 대비 인수가격은 비교 거래 중앙값보다 49.0% 낮습니다."
    )


def test_the_subject_name_is_not_repeated_in_the_overview() -> None:
    assert "Sample Investment Co." not in _overview()
