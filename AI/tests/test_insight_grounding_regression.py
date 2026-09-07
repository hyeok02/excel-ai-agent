"""Source-grounding regressions: synthetic workbooks only, never live LLM calls."""

import pytest

from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.validator import validate_workbook_insights


def source_context(label="급식 열량", value=750, sentence="급식 열량은 750 kcal입니다."):
    return {
        "omitted_sheet_count": 0,
        "sheets": [{
            "name": "Sheet1",
            "business_facts": {"selected_records": [{
                "location": "Sheet1!A2:C2",
                "values": [
                    {"cell": "A2", "value": label},
                    {"cell": "B2", "value": value},
                    {"cell": "C2", "value": sentence},
                ],
            }]},
        }],
    }


def candidate(fact="급식 열량은 750 kcal입니다.", **changes):
    fields = dict(
        title="급식 열량", fact=fact, category="summary", severity="info",
        evidence=["Sheet1!A2:C2"], confidence=0.95,
    )
    fields.update(changes)
    return WorkbookInsightReport(
        overview="Riot Games의 직원 수가 감소했습니다.",
        insights=[WorkbookInsight(**fields)],
        limitations=["Riot Games의 인력 감축 원인은 별도 확인해야 합니다."],
    )


@pytest.mark.parametrize("fact", [
    "Riot Games의 직원 수는 750명입니다.",
    "학생들의 평균 점수는 750점입니다.",
    "급식 열량은 999 kcal입니다.",
])
def test_blocks_invented_subjects_and_unmatched_numbers(fact):
    result = validate_workbook_insights(candidate(fact), source_context())

    assert result.validation.blocked_count == 1
    assert fact not in result.model_dump_json()
    assert "Riot Games" not in result.model_dump_json()


@pytest.mark.parametrize("evidence", [
    ["Other!A2:C2"], ["Sheet1!Z999"],
    ["Sheet1!A2:C2", "Other!Z999"],
    ["위치를 확인할 수 없는 분석 결과"],
])
def test_blocks_unresolvable_or_partly_fabricated_citations(evidence):
    result = validate_workbook_insights(candidate(evidence=evidence), source_context())

    assert result.validation.blocked_count == 1


def test_evidence_prose_cannot_supply_its_own_subject_grounding():
    report = candidate(
        "Riot Games의 직원 수는 750명입니다.",
        evidence=["Sheet1!A2:C2 — Riot Games 직원 수 750명"],
        recommendation="Riot Games의 인력 감축 계획을 검토하세요.",
    )
    result = validate_workbook_insights(report, source_context())

    assert result.validation.blocked_count == 1
    assert "Riot Games" not in result.model_dump_json()


def test_numbers_from_an_unrelated_row_cannot_validate_a_cited_row():
    context = source_context()
    context["sheets"][0]["business_facts"]["selected_records"].append({
        "location": "Sheet1!A8:C8",
        "values": [{"cell": "A8", "value": "재료비"}, {"cell": "B8", "value": 999}],
    })
    result = validate_workbook_insights(
        candidate("급식 열량은 999 kcal입니다."), context,
    )

    assert result.validation.blocked_count == 1
    assert "급식 열량은 999" not in result.model_dump_json()


def test_blocked_fact_cannot_leak_through_any_report_surface():
    invented = "Riot Games의 직원 수는 6,101명에서 5,417명으로 684명 감소했습니다."
    report = candidate(
        invented, title="Riot Games 인력 감소", cause="Riot Games의 구조조정 때문입니다.",
        impact="Riot Games의 인력 부담이 커집니다.",
        recommendation="Riot Games의 인력 감축 계획을 검토하세요.",
    )
    result = validate_workbook_insights(report, source_context())

    assert result.validation.generated_count >= 1
    assert result.validation.blocked_count == 1
    for forbidden in ("Riot Games", "6,101", "5,417", "인력 감축", "구조조정"):
        assert forbidden not in result.model_dump_json()


@pytest.mark.parametrize(("label", "value", "fact"), [
    ("급식 열량", 750, "급식 열량은 750 kcal입니다."),
    ("2공장 생산량", 120, "2공장 생산량은 120개입니다."),
    ("예산 집행액", 45000, "예산 집행액은 45,000원입니다."),
])
def test_keeps_legitimate_cited_source_facts_across_domains(label, value, fact):
    result = validate_workbook_insights(
        candidate(fact, title=label), source_context(label, value, fact),
    )

    assert result.validation.blocked_count == 0
    assert any(item.fact == fact for item in result.insights)
    assert "Riot Games" not in result.model_dump_json()


def test_verified_fact_cannot_smuggle_an_unrelated_title_or_recommendation():
    report = candidate(
        title="Riot Games 인력 현황",
        impact="Riot Games의 750명에 대한 구조조정이 필요합니다.",
        recommendation="Riot Games의 인력 감축을 진행하세요.",
    )
    result = validate_workbook_insights(report, source_context())

    assert "Riot Games" not in result.model_dump_json()
    assert "구조조정" not in result.model_dump_json()
