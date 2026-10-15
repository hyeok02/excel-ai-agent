"""Conservative lexical grounding for workbook answers."""
from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.grounding_sources import (
    REPORTING_LANGUAGE,
    cited_references,
    evidence_sources,
    semantic_units,
)
from app.agent.query.references import matching_references, normalize_reference
from app.agent.query.translated_evidence import translated_evidence_sources
from app.agent.query.semantic_safety import semantic_claim_supported
from app.agent.query.verified_insight_constraints import (
    insight_intent_matches,
    requested_identifiers_match,
)
from app.agent.query.verified_insight_matching import MIN_RELEVANCE_SCORE, verified_insight_score

def answer_is_grounded(
    answer: str,
    evidence: list[object],
    execution: AgentExecution,
    question: str = "",
) -> bool:
    if not requested_identifiers_match(question.casefold(), answer.casefold()):
        return False
    references = cited_references(evidence)
    facts = _covered_verified_facts(execution, references)
    if not semantic_claim_supported(answer, evidence, facts):
        return False
    sources = [*evidence_sources(evidence), REPORTING_LANGUAGE]
    sources.extend(translated_evidence_sources(evidence))
    sources.extend(semantic_units(sources))
    sources.extend(facts)
    from app.services.insights.verification.claim_grounding import grounded_claim

    return bool(sources) and grounded_claim(answer, sources, references)

def verified_fallback_answer(
    question: str, evidence: list[object], execution: AgentExecution
) -> str | None:
    references = cited_references(evidence)
    facts = _covered_verified_items(execution, references)
    if not facts:
        return None
    def score(item):
        return verified_insight_score(question, question, item)

    ranked = sorted(facts, key=score, reverse=True)
    kind = _answer_kind(execution)
    relevant = [
        str(item.get("fact") or "").strip()
        for item in ranked
        if score(item) >= MIN_RELEVANCE_SCORE
        and insight_intent_matches(question, item, kind)
    ]
    return " ".join(item for item in relevant[:3] if item) or None

def verified_support_references(
    question: str, evidence: list[object], execution: AgentExecution
) -> list[str]:
    cited = cited_references(evidence)
    candidates = []
    for fact in _verified_items(execution):
        score = verified_insight_score(question, question, fact)
        if score < MIN_RELEVANCE_SCORE or not insight_intent_matches(
            question, fact, _answer_kind(execution)
        ):
            continue
        support = [
            value
            for value in fact.get("support_references", [])
            if isinstance(value, str) and normalize_reference(value)
        ]
        trigger = fact.get("trigger_references", support)
        normalized_triggers = [
            normalized
            for value in trigger
            if isinstance(value, str)
            if (normalized := normalize_reference(value))
        ]
        covered_citations = {
            citation
            for reference in normalized_triggers
            for citation in matching_references(reference, cited)
        }
        # A range is less specific than a point: require two independently cited
        # cells before expansion. matching_references also rejects huge ranges.
        uses_range = any(":" in reference for reference in normalized_triggers)
        required_overlap = 2 if uses_range else min(2, len(normalized_triggers))
        if required_overlap and len(covered_citations) >= required_overlap:
            candidates.append((score, support))
    ranked = sorted(candidates, key=lambda item: item[0], reverse=True)
    return list(dict.fromkeys(value for _, support in ranked for value in support))

def _covered_verified_facts(
    execution: AgentExecution, references: set[str]
) -> list[str]:
    return [
        str(item[key])
        for item in _covered_verified_items(execution, references)
        for key in ("fact",)
        if item.get(key)
    ]


def _covered_verified_items(
    execution: AgentExecution, references: set[str]
) -> list[dict[str, object]]:
    sources = []
    for fact in _verified_items(execution):
        required = {
            normalized
            for value in fact.get(
                "support_references", fact.get("required_references", [])
            )
            if isinstance(value, str)
            if (normalized := normalize_reference(value))
        }
        if required and all(matching_references(item, references) for item in required):
            sources.append(fact)
    return sources


def _verified_items(execution):
    for step in execution.steps:
        if step.status is AgentStepStatus.SUCCEEDED and step.result:
            facts = step.result.data.get("verified_insights")
            if isinstance(facts, list):
                yield from (fact for fact in facts if isinstance(fact, dict))


def _answer_kind(execution) -> str:
    return next(
        (
            str(step.result.data.get("answer_kind") or "")
            for step in execution.steps
            if step.result and isinstance(step.result.data, dict)
        ),
        "",
    )
