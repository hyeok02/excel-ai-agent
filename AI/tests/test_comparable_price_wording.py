"""Other layouts and languages follow the same price/size rules."""
from app.services.insights.narratives.comparable_narratives import comparable_transaction_report
from tests.test_comparable_price_basis import _context, _regions

KOREAN = ["피인수기업명", "인수자", "발표일", "업종", "거래금액(억원)", "EV/EBITDA(배)", "P/E(배)"]


def _korean(subject_industry="보험", pe=None):
    peers = [(f"기업{i}", f"인수자{i}", "2024-0{}-01".format(i + 1), "은행" if i < 4 else "증권",
              1000.0 + 100 * i, 6.0 + i, (pe or [8.0 + i for i in range(6)])[i]) for i in range(6)]
    subject = ("대상기업", "매수회사", "2024-09-15", subject_industry, 900.0, 5.0, 12.0)
    return _regions("비교 거래 분석", KOREAN, peers, "A", subject, labels=("최대", "중앙값", "최소"))


def test_korean_headers_report_each_full_coverage_multiple_and_size():
    facts, context = _context(_korean())
    items, overview = comparable_transaction_report(context)
    assert [item.topic for item in items] == ["EBITDA 대비 인수가격", "순이익 대비 인수가격", "거래 규모"]
    assert items[0].fact.startswith("대상기업의 EBITDA 대비 인수가격은 5.00배로, 비교 거래 6건의 중앙값 8.50배보다")
    assert "1,250.0억원" in items[2].fact and "900.0억원" in items[2].fact
    assert overview.startswith("EBITDA 대비 인수가격은 비교 거래 중앙값보다 41.2% 낮습니다.")
    assert "같은 업종(보험)은 없어, 싸게 인수했다고 단정하기는 어렵습니다" in overview
    assert facts["buyer"] == "매수회사" and facts["announced"] == "2024-09-15"


def test_shared_industry_or_higher_multiple_changes_only_the_wording():
    overview = comparable_transaction_report(_context(_korean("은행"))[1])[1]
    assert "업종" not in overview
    pe = [4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    high = _korean(pe=pe)
    for region in high:  # EV/EBITDA for half of the peers: still usable, ranked after P/E
        for row in region["analysis_rows"]:
            if row[0]["address"][:1] == "G" and row[0]["address"][1:] in {"12", "13", "14"}:
                row[0]["value"] = "NA"
    items, overview = comparable_transaction_report(_context(high)[1])
    assert [item.topic for item in items][:2] == ["순이익 대비 인수가격", "EBITDA 대비 인수가격"]
    assert "84.6% 높습니다" in items[0].fact and "6건 중 값이 있는 3건의" in items[1].fact
    assert "비싸게 인수했다고 단정하기는 어렵습니다" in overview


def test_without_a_usable_multiple_only_size_is_compared():
    headers = ["Target/Issuer Name", "Total Transaction Value ($M)", "Deal Value/ EBITDA (x)"]
    peers = [(f"P{i}", 100.0 + 10 * i, 9.0 if i < 3 else "NA") for i in range(8)]
    _, context = _context(_regions("Transaction comparables", headers, peers, "A", ("Focus", 90.0, 5.0)))
    items, overview = comparable_transaction_report(context)
    assert [item.topic for item in items] == ["거래 규모"]
    assert overview == ("EBITDA 기준 배수가 8건 중 3건만 값이 있어 가격 수준은 판단할 수 없습니다. "
                        "비교할 수 있는 것은 거래 규모뿐이며, 비교 거래 중앙값보다 33.3% 작습니다.")


def test_buyer_earnings_alone_never_become_a_target_multiple():
    headers = ["Target/Issuer Name", "Implied Equity Value ($M)", "Net Income ($M)",
               "Total Transaction Value ($M)"]
    peers = [(f"P{i}", 500.0 + i, 40.0 + i, 600.0 + i) for i in range(6)]
    regions = _regions("Comparable transactions", headers, peers, "A", ("Focus", 450.0, 30.0, 520.0),
                       captions={4: "Acquirer LTM Financials"})
    facts, _ = _context(regions)
    assert [item["kind"] for item in facts["metrics"]] == ["size"]
