"""Reuse deterministic insight facts as trusted Q&A context."""
from app.agent.query.verified_calculation_context import (
    comparable_count_specs,
    fact_calculations,
)
from app.agent.query.references import (
    extract_references,
    matching_references,
    normalize_reference,
)
from app.services.workbook_parsing.models import WorkbookSummary

MAX_INSIGHTS = 5
MAX_CALCULATIONS = 10


def build_verified_question_context(summary: WorkbookSummary) -> dict[str, object]:
    context = _build_context(summary)
    report = _source_report(context)
    calculations, descriptions = fact_calculations(context)
    calculations = _select_calculations(calculations, report.insights)
    insights = [
        {
            "title": item.title,
            "fact": item.fact,
            "evidence": item.evidence,
            "required_references": _required_references(item.evidence),
            "support_references": _required_references(item.evidence),
            "trigger_references": _trigger_references(item.evidence, calculations),
        }
        for item in report.insights[:MAX_INSIGHTS]
    ]
    references = _priority_references(insights, calculations)
    return {
        "overview": report.overview,
        "insights": insights,
        "calculations": calculations,
        "count_specs": comparable_count_specs(context),
        "priority_references": references,
        "reference_descriptions": descriptions,
    }


def _priority_references(insights, calculations):
    references = []
    for calculation in calculations:
        references.extend(calculation["operand_references"])
    for item in insights:
        for evidence in item["evidence"]:
            references.extend(extract_references(str(evidence)))
    return list(dict.fromkeys(references))


def _required_references(evidence):
    return [
        reference
        for item in evidence
        for reference in extract_references(str(item))
    ]


def _trigger_references(evidence, calculations):
    required = _required_references(evidence)
    singles = set(reference for reference in required if ":" not in reference)
    operands = [
        reference
        for calculation in calculations
        for reference in calculation.get("operand_references", [])
        if isinstance(reference, str)
        if normalize_reference(reference) in singles
    ]
    return list(dict.fromkeys(operands)) or required


def _select_calculations(calculations, insights):
    references = {
        reference
        for insight in insights[:MAX_INSIGHTS]
        for reference in _required_references(insight.evidence)
    }

    def score(calculation):
        operands = [
            normalize_reference(value)
            for value in calculation.get("operand_references", [])
        ]
        return sum(
            any(matching_references(reference, {operand}) for reference in references)
            for operand in operands
            if operand
        )

    ranked = sorted(enumerate(calculations), key=lambda item: (-score(item[1]), item[0]))
    return [item for _, item in ranked[:MAX_CALCULATIONS]]


def _build_context(summary):
    from app.services.insights.context import build_workbook_context

    return build_workbook_context(summary)


def _source_report(context):
    from app.services.insights.source_narratives import source_narrative_report

    return source_narrative_report(context)
