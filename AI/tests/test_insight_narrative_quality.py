import re

import pytest

from app.services.insights.models import WorkbookInsightReport
from app.services.insights.quality import build_source_report
from app.services.insights.reference_matching import matching_references
from app.services.insights.validation_index import extract_references
from app.services.insights.validator import validate_workbook_insights
from tests.support.narrative_contexts import source_records, trend_context


def validated(context):
    return validate_workbook_insights(build_source_report(context), context)


def covers(insight, address):
    citations = set().union(*(extract_references(item) for item in insight.evidence))
    return any(matching_references(citation, {address.casefold()}) for citation in citations)


def contains_number(text, number):
    return re.search(rf"(?<![\d.]){number}(?![\d.])", text.replace(",", "")) is not None


@pytest.mark.parametrize("metrics", [
    ("전체 인원", "기획 부문", "운영 부문"),
    ("합계 출고량", "품목 가", "품목 나"),
])
def test_overall_metric_precedes_smaller_components_with_larger_relative_changes(metrics):
    context = trend_context(metrics)
    result = validated(context)

    assert result.insights, "Source-grounded narratives must remain visible."
    assert metrics[0] in result.insights[0].fact
    assert result.overview.index(metrics[0]) < result.overview.index(metrics[2])
    assert contains_number(result.insights[0].fact, 1000)
    assert contains_number(result.insights[0].fact, 900)


def test_subject_is_named_only_alongside_its_actual_identity_cell_evidence():
    result = validated(trend_context())
    subject_insights = [item for item in result.insights if "푸른연구원" in item.fact]

    assert subject_insights, "An addressable identity row should contribute useful context."
    assert "푸른연구원" in result.overview
    for insight in subject_insights:
        assert covers(insight, "현황!B1")
        assert any(covers(insight, address) for address in (
            "현황!B4", "현황!B5", "현황!B6", "현황!C6", "현황!D6",
        ))


def test_unaddressable_identity_cannot_be_attached_to_an_otherwise_valid_trend():
    context = trend_context()
    identity = source_records(context)[0]
    identity.pop("location")
    for value in identity["values"]:
        value.pop("cell")

    result = validated(context)

    assert result.insights
    assert "푸른연구원" not in result.model_dump_json()


def test_total_time_series_preserves_middle_period_and_cites_that_source_row():
    result = validated(trend_context())
    total = next(item for item in result.insights if "전체 인원" in item.fact)

    assert all(contains_number(total.fact, number) for number in (1000, 950, 900))
    assert covers(total, "현황!B4")
    assert covers(total, "현황!B5")
    assert covers(total, "현황!B6")
    assert "2025" in total.fact


def test_components_are_explained_together_instead_of_unrelated_percentage_cards():
    result = validated(trend_context())
    grouped = [item for item in result.insights
               if "기획 부문" in item.fact and "운영 부문" in item.fact]

    assert grouped, "Related components need a coherent, shared summary."
    assert any(contains_number(item.fact, 585) and contains_number(item.fact, 315)
               for item in grouped)
    for item in grouped:
        assert covers(item, "현황!C6")
        assert covers(item, "현황!D6")


def test_manufacturing_summary_never_invents_a_person_or_currency_unit():
    context = trend_context(("전체 생산", "압출 라인", "성형 라인"))
    source_records(context)[0]["values"][1]["value"] = "서부 공장"

    result = validated(context)

    assert result.insights
    assert not re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:명|원|달러)", result.overview)
    assert not re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:명|원|달러)",
                         " ".join(item.fact for item in result.insights))


def test_explicit_person_count_format_supplies_the_narrative_unit():
    result = validated(trend_context(unit="명"))

    assert result.insights
    assert re.search(r"\d[\d,]*\s*명", " ".join(item.fact for item in result.insights))


def test_validated_overview_uses_source_narrative_not_the_raw_model_overview():
    context = trend_context()
    source = build_source_report(context)
    draft = WorkbookInsightReport(
        overview="외계 회사의 직원 999999명이 전원 해고됐습니다.",
        insights=source.insights,
        limitations=["외계 회사의 경영 상황을 확인해야 합니다."],
    )

    result = validate_workbook_insights(draft, context)

    assert "외계 회사" not in result.model_dump_json()
    assert "999999" not in result.model_dump_json()
    assert result.validation.model_dump().get("overview_validated") is True
    assert "전체 인원" in result.overview
    assert "기획 부문" in result.overview
    assert "운영 부문" in result.overview


def test_copying_a_canonical_fact_without_identity_evidence_does_not_bypass_validation():
    context = trend_context()
    source = build_source_report(context)
    original = next(item for item in source.insights if "푸른연구원" in item.fact)
    unsupported = original.model_copy(update={"evidence": ["현황!A4:D6"]})
    draft = WorkbookInsightReport(overview=original.fact, insights=[unsupported])

    result = validate_workbook_insights(draft, context)

    assert result.validation.blocked_count >= 1
    for item in result.insights:
        if "푸른연구원" in item.fact:
            assert covers(item, "현황!B1")
