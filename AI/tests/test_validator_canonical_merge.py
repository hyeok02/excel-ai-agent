"""Validated model details must not disappear behind a full canonical report."""
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.source_narratives import source_narrative_report
from app.services.insights.validator import _duplicate, validate_workbook_insights


def _cell(address, value):
    return {"cell": address, "value": value, "number_format": "General"}


def _context():
    regions = []
    for index in range(5):
        row = index * 3 + 2
        regions.append({"rows": [
            [_cell(f"A{row - 1}", "Rank"), _cell(f"B{row - 1}", "Name"),
             _cell(f"C{row - 1}", "Shares Held"),
             _cell(f"D{row - 1}", "Share (%)")],
            [_cell(f"A{row}", 1), _cell(f"B{row}", f"Fund {index + 1}"),
             _cell(f"C{row}", 1_000 - index), _cell(f"D{row}", 40 - index)],
        ]})
    return {"sheets": [{"name": "Ownership", "business_facts": {
        "table_regions": regions,
        "selected_records": [{
            "location": "Ownership!F20",
            "values": [{"cell": "F20", "value": "별도 확인 사항"}],
        }],
    }}]}


def test_independently_grounded_model_finding_keeps_one_visible_slot():
    context = _context()
    finding = WorkbookInsight(
        title="별도 확인 사항", fact="별도 확인 사항", category="summary",
        severity="info", evidence=["Ownership!F20"], confidence=1,
    )
    draft = WorkbookInsightReport(overview=finding.fact, insights=[finding])

    result = validate_workbook_insights(draft, context)

    assert len(result.insights) == 5
    assert any(item.fact == "별도 확인 사항" for item in result.insights)


def test_same_cells_subject_and_numbers_are_a_duplicate_when_rephrased():
    canonical = source_narrative_report(_context()).insights[0]
    paraphrase = canonical.model_copy(update={
        "fact": "Fund 1은 1위이고 보유 주식 수는 1,000, 비중은 40%입니다.",
    })

    assert _duplicate(paraphrase, [canonical])
