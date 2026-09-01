import re

from app.agent.writeback.models import WritebackChange
from app.agent.writeback.references import (
    MAX_CHANGES,
    affected_cells,
    context_cells,
    expand_reference,
    key,
)

FORBIDDEN_FORMULA = re.compile(
    r"(?:\[|https?://|\\\\|\||\b(?:WEBSERVICE|HYPERLINK|RTD|CALL|REGISTER\.ID|EXEC)\s*\()",
    re.IGNORECASE,
)


def validate_changes(
    drafts, available, data_index, instruction: str
) -> tuple[list[WritebackChange], list[str]]:
    changes, risks, seen = [], [], set()
    for draft in drafts:
        references = expand_reference(draft.reference)
        if not references:
            risks.append(
                f"{draft.sheet_name}!{draft.reference}: 올바른 셀 또는 범위 주소가 아닙니다."
            )
            continue
        if len(changes) + len(references) > MAX_CHANGES:
            risks.append(
                f"{draft.sheet_name}!{draft.reference}: 한 번에 {MAX_CHANGES}개 셀까지 변경할 수 있어 제외했습니다."
            )
            continue
        for reference in references:
            _append_change(
                changes, risks, seen, draft, reference, available, data_index, instruction
            )
    return changes, risks


def _append_change(
    changes, risks, seen, draft, reference, available, data_index, instruction
) -> None:
    cell_key = key(draft.sheet_name, reference)
    cell = available.get(cell_key)
    if cell is None:
        risks.append(f"{draft.sheet_name}!{reference}: 원본에서 확인할 수 없는 셀입니다.")
        return
    if cell_key in seen:
        risks.append(f"{draft.sheet_name}!{reference}: 중복 변경입니다.")
        return
    seen.add(cell_key)
    formula = _formula_value(draft.new_value)
    if cell.formula and formula is None:
        risks.append(
            f"{draft.sheet_name}!{reference}: 수식 셀은 명시적인 새 수식으로만 변경할 수 있습니다."
        )
        return
    formula_risk = _formula_risk(formula, instruction)
    if formula_risk:
        risks.append(f"{draft.sheet_name}!{reference}: {formula_risk}")
        return
    old_value = cell.formula or cell.value
    if draft.new_value == old_value:
        risks.append(f"{draft.sheet_name}!{reference}: 기존 값과 동일합니다.")
        return
    affected = affected_cells(data_index, cell.sheet_name, reference)
    change_type = "formula" if formula else "clear" if draft.new_value is None else "value"
    payload = draft.model_dump()
    payload["reference"] = reference
    changes.append(
        WritebackChange(
            **payload,
            old_value=old_value,
            context_cells=context_cells(data_index, cell),
            change_type=change_type,
            value_type=_value_type(draft.new_value, cell.value_type, change_type),
            affected_cells=affected,
            risk_level=_risk_level(change_type, affected),
        )
    )


def _formula_value(value: object) -> str | None:
    if isinstance(value, str) and value.lstrip().startswith("="):
        return value.strip()
    return None


def _formula_risk(formula: str | None, instruction: str) -> str | None:
    if formula is None:
        return None
    if formula.casefold() not in instruction.casefold():
        return "수식 원문이 요청에 직접 적혀 있지 않아 제외했습니다."
    if len(formula) > 8192:
        return "Excel 수식 최대 길이를 초과했습니다."
    if FORBIDDEN_FORMULA.search(formula):
        return "외부 연결이나 실행 기능이 포함된 수식은 허용하지 않습니다."
    return None


def _value_type(value: object, current_type: str, change_type: str) -> str:
    if change_type == "formula":
        return "formula"
    if change_type == "clear":
        return "blank"
    if current_type in {"date", "datetime"} and isinstance(value, str):
        return current_type
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "text"


def _risk_level(change_type: str, affected: list[str]) -> str:
    if len(affected) > 8:
        return "high"
    if change_type == "formula" or affected:
        return "medium"
    return "low"
