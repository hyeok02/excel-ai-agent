import math
import re

from app.services.insights.models import WorkbookInsight

MAX_RECORD_VALUES = 5
CELL_ADDRESS = re.compile(r"^[A-Z]{1,3}[1-9]\d*$", re.IGNORECASE)


def source_record_insights(
    context: dict[str, object], limit: int
) -> list[WorkbookInsight]:
    """Quote actual selected cells without assigning them a new domain or meaning."""
    if limit <= 0:
        return []
    candidates = []
    for sheet in context.get("sheets", []):
        name = str(sheet.get("name", ""))
        if not name:
            continue
        for record in sheet.get("business_facts", {}).get("selected_records", []):
            values = [value for value in record.get("values", []) if _usable(value)]
            if not values:
                continue
            numeric = sum(isinstance(value["value"], (int, float)) for value in values)
            has_label = any(isinstance(value["value"], str) for value in values)
            if not has_label and not any(value.get("label") for value in values):
                continue
            text_size = sum(
                len(str(value["value"]))
                for value in values
                if isinstance(value["value"], str)
            )
            candidates.append(((bool(numeric), text_size), name, values[:MAX_RECORD_VALUES]))
    candidates.sort(key=lambda item: item[0], reverse=True)
    insights = []
    seen: set[tuple[str, ...]] = set()
    for _, sheet, values in candidates:
        evidence = [_reference(sheet, str(value["cell"])) for value in values]
        signature = tuple(evidence)
        if signature in seen:
            continue
        seen.add(signature)
        insights.append(_record_insight(values, evidence))
        if len(insights) >= limit:
            break
    return insights


def _record_insight(
    values: list[dict[str, object]], evidence: list[str]
) -> WorkbookInsight:
    first = values[0]
    raw_title = first["value"] if isinstance(first["value"], str) else first.get("label")
    title = _text(raw_title) if raw_title else ""
    if not title or len(title) > 70:
        title = "원본 내용 확인"
    details = []
    for value in values:
        raw = _text(value["value"])
        details.append(raw)
    fact = " · ".join(f"‘{detail}’" for detail in details)
    return WorkbookInsight(
        title=title,
        fact=f"원본에 기록된 내용은 {fact}입니다.",
        cause=None,
        impact=None,
        category="summary",
        severity="info",
        evidence=evidence,
        recommendation=None,
        confidence=0.99,
    )


def _usable(value: object) -> bool:
    if not isinstance(value, dict) or not CELL_ADDRESS.fullmatch(
        str(value.get("cell", ""))
    ):
        return False
    raw = value.get("value")
    if isinstance(raw, bool) or raw is None or raw == "":
        return False
    if isinstance(raw, float) and not math.isfinite(raw):
        return False
    return isinstance(raw, (str, int, float)) and len(str(raw)) <= 240


def _text(value: object) -> str:
    return " ".join(str(value).split())


def _reference(sheet: str, address: str) -> str:
    escaped = sheet.replace("'", "''")
    return f"'{escaped}'!{address}"
