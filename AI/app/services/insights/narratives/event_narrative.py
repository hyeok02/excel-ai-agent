"""Readable source-only cards for dated text records."""
from app.services.insights.display.display_quality import is_field_label
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.models import WorkbookInsight
from app.services.insights.narratives.narrative_values import period, reference


def build_event_insight(sheet, values):
    dates = [cell for cell in values if date_value(cell.get("value"))]
    texts = [cell for cell in values if isinstance(cell.get("value"), str)
             and not date_value(cell.get("value"))]
    labels = [cell for cell in values if is_field_label(
        cell.get("label"), cell.get("value"),
    )]
    if not dates or len(texts) < 2 or len(labels) >= 2:
        return None
    descriptive = [cell for cell in texts if len(_text(cell["value"])) >= 45]
    headline = min(descriptive or [
        cell for cell in texts if len(_text(cell["value"])) >= 20
    ], key=lambda cell: len(_text(cell["value"])), default=None)
    if headline is None:
        return None
    category = next((cell for cell in texts if cell is not headline
                     and len(_text(cell["value"])) <= 60), None)
    date = dates[0]
    fact = (f"{period(date['value'])}에 ‘{_text(headline['value'])}’이 "
            "기록되어 있습니다.")
    used = [date, headline]
    if category:
        fact += f" 함께 표시된 항목은 ‘{_text(category['value'])}’입니다."
        used.append(category)
    title = _text(category["value"] if category else headline["value"])
    if len(title) > 70:
        title = "원본에서 확인한 내용"
    return WorkbookInsight(
        title=title, fact=fact, category="summary", severity="info",
        evidence=[reference(sheet, cell["cell"]) for cell in used], confidence=1.0,
    )


def _text(value):
    return " ".join(str(value).split())
