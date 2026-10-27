"""Validate model-selected matrix axes using tool-produced structural proofs."""
from app.agent.execution import AgentStepStatus
from app.agent.query.references import extract_references, matching_references, normalize_reference
from app.agent.query.matrix_request_scope import matrix_request_supported, mentioned_matrix_sheets


def matrix_claim_binding(value, subject, prop, period, question, execution):
    key = _reference(value)
    proofs, headers = [], []
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        mapping = step.result.data.get("source_matrix_bindings", {})
        if isinstance(mapping, dict) and key in mapping:
            proofs.append(mapping[key])
        mapping = step.result.data.get("source_header_bindings", {})
        if isinstance(mapping, dict) and key in mapping:
            headers.append(mapping[key])
    if not proofs:
        return None
    # False means a matrix proof exists but this claim/request contradicts it;
    # callers must not fall back to a weaker ordinary-row adjacency check.
    if any(proof != proofs[0] for proof in proofs):
        return False
    proof = proofs[0]
    if not isinstance(proof, dict):
        return False
    row_ref, col_ref = proof.get("row_reference"), proof.get("column_reference")
    # Generators use both ordinary-row and matrix field conventions. Normalize
    # roles from proved coordinates, never invent an axis missing from claims.
    supplied = {_reference(item): item for item in (subject, prop, period) if item is not None}
    if (set(supplied) != {row_ref, col_ref}
            or any(header != col_ref for header in headers)):
        return False
    for item, field in ((value, "value"), (supplied[row_ref], "row_value"), (supplied[col_ref], "column_value")):
        if type(item.value) is not type(proof.get(field)) or item.value != proof.get(field):
            return False
    if not _unique_selection(question, key, proof) or not matrix_request_supported(question, proof):
        return False
    return proof


def _unique_selection(question, selected, proof):
    alternatives = proof.get("alternatives", [])
    if not alternatives or not all(isinstance(item, dict) for item in alternatives):
        return False
    asked = extract_references(question)
    if asked:
        selected_alternatives = {item.get("reference") for item in alternatives
                                 if any(matching_references(bound, {item.get("reference", "")}) for bound in asked)}
    else:
        named = mentioned_matrix_sheets(question, proof)
        if proof.get("unavailable_sheets") and (not named or named & set(proof["unavailable_sheets"])):
            return False
        selected_alternatives = {item.get("reference") for item in alternatives if not named or item.get("sheet") in named}
    return selected_alternatives == {selected}


def _reference(item):
    return normalize_reference(f"{item.sheet_name}!{item.reference}")


def matrix_evidence_descriptions(selected, proof):
    """Replace guessed retrieval context only after the matrix binding is proved."""
    descriptions = {
        proof["row_reference"]: f"교차표 행 항목: {proof['row_value']}",
        proof["column_reference"]: f"교차표 열 항목: {proof['column_value']}",
        proof["value_reference"]: f"교차표 원본 값: {proof['row_value']} / {proof['column_value']}",
    }
    return [item.model_copy(update={"description": descriptions[_reference(item)]})
            if _reference(item) in descriptions else item for item in selected]
