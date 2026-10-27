"""Resolve structured claims against current tool evidence and render source values."""
import re
from dataclasses import dataclass

from app.agent.execution import AgentStepStatus
from app.agent.query.claim_scope import claim_scope_matches
from app.agent.query.comparison_evidence import matched_comparison_evidence
from app.agent.query.references import normalize_reference
from app.agent.query.source_claim_matrix import matrix_claim_binding, matrix_evidence_descriptions
from app.agent.query.matrix_request_scope import plain_matrix_lookup
from app.agent.query.verified_insight_constraints import insight_intent_matches
from app.agent.query.verified_insight_matching import MIN_RELEVANCE_SCORE, verified_insight_score

CELL = re.compile(r"([A-Z]+)([1-9]\d*)", re.I)


@dataclass(frozen=True)
class RenderedClaim:
    sentence: str
    evidence: list
    complete_lookup: bool = False


def render_claim(claim, question, available, execution):
    if claim.kind == "unknown":
        return None
    if claim.kind == "verified_fact":
        return _verified_fact(claim, question, available, execution)
    if claim.fact is not None:
        return None
    refs = [claim.value_reference, claim.subject_reference, claim.property_reference, claim.period_reference]
    values = [_point(value, available) if value else None for value in refs]
    value, subject, prop, period = values
    if value is None or any(ref and item is None for ref, item in zip(refs, values)):
        return None
    if value.value is None or any(item and item.formula for item in (subject, prop, period)):
        return None
    matrix = matrix_claim_binding(value, subject, prop, period, question, execution)
    if matrix is False:
        return None
    if not matrix and any(item and not _same_row(value, item) for item in (subject, period)):
        return None
    if not matrix and prop and not _property_matches(value, prop, execution):
        return None
    evidence = list(dict.fromkeys(ref for ref in refs if ref))
    selected = [available[normalize_reference(ref)] for ref in evidence]
    if not claim_scope_matches(question, selected, available, normalize_reference(claim.value_reference)):
        return None
    if matrix:
        selected = matrix_evidence_descriptions(selected, matrix)
        prop, period = available[matrix["row_reference"]], available[matrix["column_reference"]]
        sentence = (f"행 항목 {_quoted(prop.value)}({_reference(prop)})과 "
                    f"열 항목 {_quoted(period.value)}({_reference(period)})의 교차점인 "
                    f"{_reference(value)}에 {_quoted(value.value)}이(가) 기록되어 있습니다.")
        return RenderedClaim(sentence, selected, plain_matrix_lookup(question, matrix))
    # Row adjacency is a structural fact, not proof of a business relationship.
    # Expose original labels and addresses; never infer symbols, polarity or causes.
    context = [f"{_quoted(item.value)}({_reference(item)})" for item in (subject, period) if item]
    prefix = f"{' · '.join(context)}와 같은 행에서, " if context else ""
    label = f"열 이름 {_quoted(prop.value)}({_reference(prop)})의 " if prop else ""
    sentence = f"{prefix}{label}{_reference(value)}에 {_quoted(value.value)}이(가) 기록되어 있습니다."
    return RenderedClaim(sentence, selected)


def _verified_fact(claim, question, available, execution):
    if any((claim.value_reference, claim.subject_reference, claim.property_reference, claim.period_reference)):
        return None
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        for fact in step.result.data.get("verified_insights", []):
            if not isinstance(fact, dict) or claim.fact != fact.get("fact"):
                continue
            references = fact.get("support_references", fact.get("required_references", []))
            if not isinstance(references, list) or not references or not all(isinstance(r, str) for r in references):
                continue
            evidence, missing = matched_comparison_evidence(references, available)
            if missing or not evidence or not claim_scope_matches(question, evidence, available):
                continue
            if not insight_intent_matches(question, fact):
                continue
            asked = re.sub(r"(값|수|열|행)(?:은|는|이|가|의|을|를)(?=\s|[?!.]|$)", r"\1", question)
            if verified_insight_score(asked, asked, fact) >= MIN_RELEVANCE_SCORE:
                return RenderedClaim(claim.fact, evidence)
    return None


def _point(reference, available):
    normalized = normalize_reference(reference)
    item = available.get(normalized)
    if item is None or not CELL.fullmatch(item.reference.replace("$", "")):
        return None
    return item


def _same_row(value, other):
    return (other is not value and value.sheet_name == other.sheet_name
            and CELL.fullmatch(value.reference.replace("$", "")).group(2)
            == CELL.fullmatch(other.reference.replace("$", "")).group(2))


def _property_matches(value, prop, execution):
    column, row = CELL.fullmatch(value.reference.replace("$", "")).groups()
    other_column, other_row = CELL.fullmatch(prop.reference.replace("$", "")).groups()
    if not (prop.sheet_name == value.sheet_name and column == other_column and int(other_row) < int(row)
            and isinstance(prop.value, str) and prop.value.strip()):
        return False
    key, expected = normalize_reference(_reference(value)), normalize_reference(_reference(prop))
    bindings = []
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        mapping = step.result.data.get("source_header_bindings")
        if isinstance(mapping, dict) and key in mapping:
            bindings.append(mapping[key])
    # When a source table establishes the binding it is authoritative; a guessed
    # description must not override a conflicting or ambiguous original header.
    if bindings:
        return all(binding == expected for binding in bindings)
    description = value.description.split(" (Excel 표시 형식:", 1)[0].strip()
    return prop.value.strip() == description


def _quoted(value):
    # A quoted workbook value remains data even if it contains instructions or Markdown.
    return "‘" + str(value).replace("\n", " ").replace("\r", " ").replace("‘", "(").replace("’", ")") + "’"


def _reference(item):
    return f"{item.sheet_name}!{item.reference}"
