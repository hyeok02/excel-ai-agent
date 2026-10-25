"""Price level comes from multiples with enough peers; amounts are deal size.

Fixtures use different header wording, languages and column sets on purpose:
the same rules must read any comparable-deal sheet, not one template.
"""
from openpyxl.utils import get_column_letter

from app.services.insights.facts.comparable_transactions import extract_comparable_transactions
from app.services.insights.narratives.comparable_narratives import comparable_transaction_report
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.insights.models import WorkbookInsightReport

NA = "NA"


def _regions(title, headers, peers, stats_label_column, subject, captions=None, hidden=(),
             labels=("High", "Median", "Low")):
    """headers: column labels; peers/subject: rows of values in the same order."""
    regions, header_row, first = [], 10, 12
    regions.append({"analysis_rows": [[{"address": "A1", "value": title}]]})
    if captions:
        regions.append({"analysis_rows": [[{"address": f"{get_column_letter(column)}{header_row - 1}",
                                            "value": text} for column, text in captions.items()]]})
    stats_row = first + len(peers) + 1
    for index, header in enumerate(headers, start=2):
        letter = get_column_letter(index)
        column = [[{"address": f"{letter}{header_row}", "value": header}]]
        column += [[{"address": f"{letter}{first + row}", "value": values[index - 2]}]
                   for row, values in enumerate(peers) if values[index - 2] is not None]
        column += [[{"address": f"{letter}{stats_row + 4}", "value": subject[index - 2]}]]
        regions.append({"analysis_rows": column,
                        "hidden_columns": [letter] if header in hidden else []})
    stats = [[{"address": f"{stats_label_column}{stats_row + offset}", "value": label}]
             for offset, label in enumerate(labels)]
    first_numeric = next(index for index, value in enumerate(subject, start=2)
                         if isinstance(value, (int, float)))
    letter = get_column_letter(first_numeric)
    values = sorted(row[first_numeric - 2] for row in peers)
    stats += [[{"address": f"{letter}{stats_row + offset}", "value": value}]
              for offset, value in enumerate((values[-1], values[len(values) // 2], values[0]))]
    regions.append({"analysis_rows": stats})
    return regions


def _context(regions, sheet="Deals"):
    facts = extract_comparable_transactions(sheet, regions)
    return facts, {"sheets": [{"name": sheet, "business_facts": {"comparable_transactions": facts}}]}


def _template_like():
    headers = ["Target/Issuer Name", "Buyer/Investor Name", "Announced Date",
               "Total Transaction Value ($M)", "Implied Equity Value ($M)",
               "Transaction Value/ EBITDA (x)", "Net Income ($M)", "Net Income ($M)",
               "Target/Issuer Primary Industry ", "Target/Issuer Primary Industry "]
    rows = [("P1", "B1", 832.5, 833.7, NA, 93.4, NA, "Financials", "Bank"),
            ("P2", "B2", 713.8, 838.8, NA, 208.7, 1688.2, "Financials", "Life"),
            ("P3", "B3", 1795.9, NA, 2.31, 266.0, 21.8, "Financials", "Mortgage"),
            ("P4", "B4", 1794.3, 1991.2, NA, 222.6, -165.5, "Financials", "Bank"),
            ("P5", "B5", 3607.9, 4575.8, NA, 213.9, 2193.0, "Financials", "Bank"),
            ("P6", "B6", 4888.7, 4240.6, 16.88, 160.6, NA, "Financials", "Tech"),
            ("P7", "B7", 833.8, 1502.1, NA, 81.2, 166.3, "Financials", "Bank"),
            ("P8", "B8", 665.0, 1144.1, NA, 47.8, NA, "Financials", "Lending"),
            ("P9", "B9", 1559.5, 1324.1, 9.99, 54.2, 176.0, "Financials", "Insurance"),
            ("P10", "B10", 422.7, 614.6, NA, 41.5, NA, "Financials", "Bank")]
    peers = [(name, buyer, "2018-03-01T00:00:00", *rest) for name, buyer, *rest in rows]
    subject = ("Focus Co.", "Acquirer Inc.", "2018-05-02T00:00:00", 911.8, 902.2, 5.09,
               66.5, 3037.7, "Financials", "Mortgage REIT")
    captions = {8: "Target LTM Financials", 9: "Acquirer LTM Financials"}
    return _regions("Comparable M&A Transactions", headers, peers, "A", subject, captions)


def test_thin_reported_multiple_gives_way_to_target_earnings_multiple():
    facts, context = _context(_template_like())
    derived = next(item for item in facts["metrics"] if item.get("derived"))
    assert derived["basis"] == "net_income"
    assert round(derived["subject_value"], 2) == round(902.2 / 66.5, 2)
    assert derived["valid_count"] == 9  # one peer has no equity value
    assert "'Deals'!H12:H21" in derived["evidence"]  # target net income, not the buyer's (I)
    assert not any("!I" in reference for reference in derived["evidence"])

    items, overview = comparable_transaction_report(context)
    assert items[0].topic == "순이익 대비 인수가격"
    assert "계산값" in overview and "EBITDA 기준 배수는 10건 중 3건만 값이 있어" in overview
    assert items[-1].topic == "거래 규모" and "싸거나 비쌌다는 뜻은 아닙니다" in items[-1].fact
    assert not any("거래 가격은" in text for text in (overview, *(item.fact for item in items)))
    validated = validate_workbook_insights(WorkbookInsightReport(overview=overview, insights=items), context)
    assert validated.overview.startswith(
        "이 파일은 Acquirer Inc.의 Focus Co. 인수 거래(2018년 5월 발표, 총 거래가치 $911.8M)를 "
        "비교 거래 10건과 비교한 자료입니다.")
    assert len(validated.insights) == len(items)


def test_specific_industry_column_states_that_no_peer_shares_the_target_industry():
    _, context = _context(_template_like())
    overview = comparable_transaction_report(context)[1]
    assert "다만 비교 거래는 Bank 5건 등이고 대상과 같은 업종(Mortgage REIT)은 없어" in overview


def test_hidden_helper_columns_are_not_used():
    headers = ["Target/Issuer Name", "Total Transaction Value ($M)", "Transaction Value/ EBITDA (x)",
               "Primary Industry"]
    peers = [(f"P{i}", 100.0 + i, 8.0 + i, "Bank") for i in range(6)]
    regions = _regions("Comparable transactions", headers, peers, "A",
                       ("Focus", 90.0, 6.0, "REIT"), hidden=("Primary Industry",))
    facts, context = _context(regions)
    assert facts["industry"] is None
    assert "업종" not in comparable_transaction_report(context)[1]
