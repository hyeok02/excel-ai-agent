import math
import re

from app.services.insights.display.display_quality import is_presentable_label
from app.services.insights.models import WorkbookInsight
from app.services.insights.narratives.narrative_values import reference
from app.services.insights.narratives.record_display import build_record_insight, record_priority
from app.services.insights.facts.sheet_scope import narrative_sheet_groups

CELL_ADDRESS = re.compile(r"^[A-Z]{1,3}[1-9]\d*$", re.IGNORECASE)


def source_record_insights(
    context: dict[str, object], limit: int
) -> list[WorkbookInsight]:
    """Quote actual selected cells without assigning them a new domain or meaning."""
    if limit <= 0:
        return []
    candidates = []
    primary, comparisons = narrative_sheet_groups(context)
    for source_order, sheet in primary or comparisons:
        name = str(sheet.get("name", ""))
        if not name:
            continue
        for record in sheet.get("business_facts", {}).get("selected_records", []):
            values = [value for value in record.get("values", []) if _usable(value)]
            if not values:
                continue
            item = build_record_insight(name, values)
            if item:
                item = item.model_copy(update={
                    "topic": item.topic or _source_topic(item, name, values),
                })
                candidates.append((record_priority(values), -source_order, item))
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    insights = []
    structured = bool(candidates and candidates[0][0][1] >= 2)
    seen: set[tuple[str, ...]] = set()
    for priority, _, item in candidates:
        if structured and priority[1] == 0:
            continue
        signature = tuple(item.evidence)
        if signature in seen:
            continue
        seen.add(signature)
        insights.append(item)
        if len(insights) >= limit:
            break
    return insights


def _source_topic(
    item: WorkbookInsight, sheet: str, values: list[dict[str, object]]
) -> str | None:
    """Use a literal source cell only when that cell is cited by the card."""
    title = item.title
    if not is_presentable_label(title):
        return None
    return next((title for cell in values
                 if isinstance(cell.get("value"), str)
                 and " ".join(cell["value"].split()) == title
                 and reference(sheet, cell["cell"]) in item.evidence), None)


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
