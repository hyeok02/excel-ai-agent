"""Readable summaries must retain source provenance, dates, and uncertainty."""
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.narratives.source_context import compact_facts
from app.services.insights.narratives.source_narratives import source_narrative_report
from app.services.insights.verification.validator import validate_workbook_insights


def item(fact):
    return WorkbookInsight(title="변화", fact=fact, category="trend", severity="info",
                           evidence=["'Data'!A2:B4"], confidence=1)


def context():
    def cell(address, value):
        return {"cell": address, "value": value, "number_format": "General"}
    rows = [
        [cell("A1", "Table 1. Electricity generation by energy source, 2025-2026")],
        [cell("A2", "Year"), cell("B2", "Total Generation")],
        [cell("A3", 2025), cell("B3", 100)],
        [cell("A4", 2026), cell("B4", 120)],
        [cell("A6", "Values for 2026 are preliminary.")],
    ]
    return {"sheets": [{"name": "Data", "business_facts": {"table_regions": [
        {"rows": rows, "rows_complete": True},
    ]}}]}


def test_overview_context_and_status_have_source_references_and_survive_validation():
    ctx = context()
    source = source_narrative_report(ctx)
    assert source.insights
    assert "에너지원별" in source.overview and "발전량" in source.overview
    assert "2026년 수치는 원본에서 잠정치" in source.overview
    assert "2025년 수치는 원본에서 잠정치" not in source.overview
    for insight in source.insights:
        assert "'Data'!A1" in insight.evidence
        assert "'Data'!A6" in insight.evidence
    result = validate_workbook_insights(source, ctx)
    assert result.validation.overview_validated
    assert result.validation.verified_count == len(source.insights)
    assert result.overview == source.overview


def test_raw_model_overview_cannot_replace_the_source_topic_or_quantity():
    ctx = context()
    source = source_narrative_report(ctx)
    bad = source.insights[0].model_copy(update={
        "title": "인원 급증", "fact": "전체 직원은 999999명입니다.",
    })
    result = validate_workbook_insights(WorkbookInsightReport(
        overview="이 파일은 999999명의 직원 명부입니다.", insights=[bad],
    ), ctx)
    assert "999999" not in result.model_dump_json()
    assert "직원 명부" not in result.overview
    assert result.validation.blocked_count >= 1
    assert result.validation.verified_count > 0


def test_missing_caption_and_note_evidence_cannot_bypass_canonical_validation():
    ctx = context()
    source = source_narrative_report(ctx)
    bad = source.insights[0].model_copy(update={"evidence": ["'Data'!A2:B4"]})
    result = validate_workbook_insights(WorkbookInsightReport(
        overview=source.overview, insights=[bad],
    ), ctx)
    assert result.validation.blocked_count >= 1
    for insight in result.insights:
        if "잠정치" in insight.fact:
            assert "'Data'!A6" in insight.evidence


def test_compaction_keeps_long_term_decline_and_recent_rebound_together():
    fact = ("지표: 1997년 5.5%에서 2024년 3.6%로 감소했습니다. "
            "기간별 값은 1997년 5.5%, 2023년 3.3%, 2024년 3.6%입니다. "
            "최근 구간은 2023년 3.3%에서 2024년 3.6%로 증가했습니다.")
    original = item(fact)
    summary = compact_facts([original])
    assert "1997년 5.5%에서 2024년 3.6%로 감소" in summary
    assert "2023년 3.3%에서 2024년 3.6%로 증가" in summary
    assert "기간별 값은" not in summary
    assert original.fact == fact


def test_compaction_drops_whole_extra_facts_instead_of_truncating_numbers_or_units():
    originals = [item("출고량은 33.25 kg입니다."), item("생산량은 44.75 kg입니다.")]
    assert compact_facts(originals, max_chars=25) == originals[0].fact
    assert originals[1].fact == "생산량은 44.75 kg입니다."


def test_compaction_keeps_company_abbreviations_and_decimal_values_intact():
    fact = "U.S. Example Co.의 금액은 1,234.56입니다. 이전 기간 대비 2.7% 증가했습니다."
    assert compact_facts([item(fact)]) == fact
