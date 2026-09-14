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


def test_both_metrics_are_stated_in_one_sentence() -> None:
    overview = _overview()

    assert overview.startswith(
        "거래 가격은 비교 대상의 중앙값보다 23.8% 낮고, 이익 대비 가격은 49.0% 낮습니다."
    )


def test_opposite_directions_keep_their_own_wording() -> None:
    overview = _overview(ebitda_percent=12.0)

    assert "23.8% 낮고, 이익 대비 가격은 12.0% 높습니다" in overview
    assert "비쌌다고 단정하기는 어렵습니다" in overview


def test_missing_profit_coverage_is_stated_once() -> None:
    overview = _overview(valid_count=3)

    assert "이익 자료가 있는 거래가 10건 중 3건뿐이라" in overview
    assert overview.count("단정하기는 어렵습니다") == 1


def test_full_coverage_drops_the_caveat() -> None:
    overview = _overview(valid_count=10)

    assert "단정하기는 어렵습니다" not in overview


def test_a_single_metric_reads_on_its_own() -> None:
    assert _overview(kinds=("transaction_value",)).startswith(
        "거래 가격은 비교 대상의 중앙값보다 23.8% 낮습니다."
    )
    assert _overview(kinds=("ebitda_multiple",)).startswith(
        "이익 대비 가격은 비교 대상의 중앙값보다 49.0% 낮습니다."
    )


def test_the_subject_name_is_not_repeated_in_the_overview() -> None:
    assert "Sample Investment Co." not in _overview()
