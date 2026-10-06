"""Build and rank source-backed record values for business facts."""
from typing import Any

from app.services.insights.facts.fact_labels import (
    resolve_fact_label,
    resolve_fact_label_cell,
)
from app.services.insights.facts.fact_trends import (
    SUBJECT_LABEL,
    date_value,
    is_identity_row,
)


def fact_value(cell, headers, schemas) -> dict[str, object] | None:
    raw = cell.get("cached_value") if cell.get("formula") else cell.get("value")
    if raw in (None, "") or str(raw).startswith("<openpyxl"):
        return None
    text = str(raw)
    if text == "#PEND" or len(text) > 240:
        return None
    address = str(cell.get("address", ""))
    result = {
        "cell": address,
        "label": resolve_fact_label(address, headers, schemas),
        "value": raw,
        "number_format": cell.get("number_format"),
    }
    if label_cell := resolve_fact_label_cell(address, headers):
        result["label_cell"] = label_cell
    return result


def record_score(values: list[dict[str, object]], role: str | None) -> int:
    numeric = sum(isinstance(value["value"], (int, float)) for value in values)
    dated = sum(date_value(value["value"]) is not None for value in values)
    labeled = sum(bool(value.get("label")) for value in values)
    identity = identity_score(values)
    role_score = {"output": 8, "data": 6, "calculation": 4}.get(role, 0)
    return role_score + numeric * 4 + dated * 3 + labeled * 2 + len(values) + identity * 10


def identity_score(values: list[dict[str, object]]) -> int:
    if not is_identity_row(values):
        return 0
    labels = " ".join(str(value.get("value", "")) for value in values[:-1])
    return 4 if SUBJECT_LABEL.search(labels) else 2


def record_location(sheet_name: str, values: list[dict[str, Any]]) -> str:
    first, last = values[0]["cell"], values[-1]["cell"]
    reference = first if first == last else f"{first}:{last}"
    return f"{sheet_name}!{reference}"
