"""Conservative lexical grounding for workbook answers."""
from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.references import matching_references, normalize_reference
from app.agent.query.search_terms import search_terms

def answer_is_grounded(
    answer: str,
    evidence: list[object],
    execution: AgentExecution,
    question: str = "",
) -> bool:
    references = _cited_references(evidence)
    sources = [question, *_evidence_sources(evidence), _reporting_language()]
    sources.extend(_semantic_units(sources))
    sources.extend(_covered_verified_facts(execution, references))
    from app.services.insights.claim_grounding import grounded_claim

    return bool(sources) and grounded_claim(answer, sources, references)

def verified_fallback_answer(
    question: str, evidence: list[object], execution: AgentExecution
) -> str | None:
    references = _cited_references(evidence)
    facts = _covered_verified_items(execution, references)
    if not facts:
        return None
    terms = search_terms(question)
    ranked = sorted(
        (
            (
                sum(
                    term in f"{item.get('title', '')} {item.get('fact', '')}".casefold()
                    for term in terms
                ),
                item,
            )
            for item in facts
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    relevant = [str(item.get("fact") or "").strip() for score, item in ranked if score]
    return " ".join(item for item in relevant[:3] if item) or None

def verified_support_references(
    question: str, evidence: list[object], execution: AgentExecution
) -> list[str]:
    cited = _cited_references(evidence)
    candidates = []
    for fact in _verified_items(execution):
        support = [
            value
            for value in fact.get("support_references", [])
            if isinstance(value, str) and normalize_reference(value)
        ]
        trigger = fact.get("trigger_references", support)
        direct = {
            normalize_reference(value)
            for value in trigger
            if isinstance(value, str) and ":" not in value
        }
        overlap = len(cited & direct)
        if overlap >= min(2, len(direct)) and direct:
            text = f"{fact.get('title', '')} {fact.get('fact', '')}".casefold()
            score = sum(term in text for term in search_terms(question))
            candidates.append((score, support))
    ranked = sorted(candidates, key=lambda item: item[0], reverse=True)
    return list(dict.fromkeys(value for _, support in ranked for value in support))

def _cited_references(evidence: list[object]) -> set[str]:
    references = set()
    for item in evidence:
        reference = getattr(item, "reference", None)
        sheet = getattr(item, "sheet_name", None)
        if reference and sheet:
            normalized = normalize_reference(f"{sheet}!{reference}")
            if normalized:
                references.add(normalized)
    return references

def _evidence_sources(evidence: list[object]) -> list[str]:
    return [
        str(value)
        for item in evidence
        for value in (
            getattr(item, "description", None),
            getattr(item, "value", None),
            getattr(item, "formula", None),
        )
        if value is not None
    ]


def _covered_verified_facts(
    execution: AgentExecution, references: set[str]
) -> list[str]:
    return [
        str(item[key])
        for item in _covered_verified_items(execution, references)
        for key in ("title", "fact")
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


def _semantic_units(sources: list[str]) -> list[str]:
    text = " ".join(sources).casefold()
    aliases = (
        (("employee", "headcount", "직원", "인원"), "직원 인원 명"),
        (("transaction", "거래"), "거래"),
        (("multiple", "(x)", "배수"), "배 배수"),
        (("$m", "million", "백만 달러"), "백만 달러"),
        (("event", "development", "announcement", "이벤트"),
         "이벤트 발표 공시 소식"),
    )
    return [words for markers, words in aliases if any(marker in text for marker in markers)]


def _reporting_language() -> str:
    return (
        "단 다만 자료 해석 신중해야 합니다 신뢰도 주의 필요합니다 대표성 한계 "
        "확인되는 확인된 것 건뿐이어서 건뿐이므로 불과"
        " 감소했고 증가했고 감소하며 증가하며"
    )
