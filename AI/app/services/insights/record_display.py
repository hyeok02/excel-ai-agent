"""Turn a bounded source row into readable, literal field/value text."""
import re

from app.services.insights.display_quality import (
    business_priority,
    is_field_label,
    is_identifier_label,
    is_machine_value,
)
from app.services.insights.event_narrative import build_event_insight
from app.services.insights.fact_trends import date_value
from app.services.insights.models import WorkbookInsight
from app.services.insights.narrative_values import finite, number, period, reference

MAX_FIELDS = 7
HEADER_ONLY = re.compile(
    r"\b(?:name|date|type|method|magnitude|currency|amount|industry|rank)\b"
    r"|이름|날짜|유형|방식|통화|금액|산업|순위",
    re.I,
)


def build_record_insight(sheet: str, values: list[dict[str, object]]):
    usable = _usable_values(values)
    event = build_event_insight(sheet, usable)
    if event:
        return event
    if len(usable) < 2 or not any(isinstance(cell.get("value"), str) for cell in usable):
        return None
    if _plain_header_row(usable):
        return None
    if sum(_display_label(cell) is not None for cell in usable) >= 2:
        usable = [cell for cell in usable if _display_label(cell) is not None]
    title_cell = _title_cell(usable)
    title = _text(title_cell.get("value")) if title_cell else "원본 내용 확인"
    if len(title) > 70:
        title = f"{title[:67]}..."
    details = " · ".join(_field(cell) for cell in usable[:MAX_FIELDS])
    numeric = sum(finite(cell.get("value")) for cell in usable)
    category = "metric" if numeric else "summary"
    evidence = [reference(sheet, cell["cell"]) for cell in usable[:MAX_FIELDS]]
    return WorkbookInsight(
        title=title,
        fact=f"확인된 내용은 {details}입니다.",
        category=category,
        severity="info",
        evidence=evidence,
        confidence=1.0,
    )


def record_priority(values: list[dict[str, object]]):
    usable = _usable_values(values)
    title = _title_cell(usable)
    dated = max(
        (date_value(cell.get("value")) for cell in usable if date_value(cell.get("value"))),
        default=None,
    )
    return (
        business_priority(title.get("value")) if title else 0,
        sum(_display_label(cell) is not None for cell in usable),
        dated.toordinal() if dated else 0,
        sum(finite(cell.get("value")) for cell in usable),
        len(usable),
    )


def _usable_values(values):
    result = []
    seen = set()
    for cell in values:
        raw = cell.get("value")
        label = cell.get("label")
        if isinstance(raw, bool) or raw in (None, "") or is_machine_value(raw):
            continue
        if label and is_identifier_label(label):
            continue
        signature = _text(raw).casefold()
        if signature in seen:
            continue
        seen.add(signature)
        result.append(cell)
    return result


def _title_cell(values):
    labeled = [cell for cell in values if _display_label(cell)
               and isinstance(cell.get("value"), str)
               and not date_value(cell.get("value"))]
    named = [cell for cell in labeled if any(
        token in str(cell.get("label", "")).casefold()
        for token in ("name", "headline", "title", "company", "회사", "기업", "항목")
    )]
    if named:
        return named[0]
    return next((cell for cell in values if isinstance(cell.get("value"), str)
                 and not date_value(cell.get("value"))), None)


def _field(cell):
    label = _display_label(cell)
    value = _display_value(cell)
    return f"‘{label}: {value}’" if label else f"‘{value}’"


def _display_label(cell):
    label = cell.get("label")
    raw = cell.get("value")
    if not is_field_label(label, raw):
        return None
    return _text(label)


def _display_value(cell):
    raw = cell.get("value")
    if date_value(raw):
        return period(raw)
    if finite(raw):
        label = str(cell.get("label", ""))
        number_format = str(cell.get("number_format", ""))
        if "%" in number_format:
            display = raw if "\\%" in number_format else float(raw) * 100
            return f"{number(display)}%"
        return f"{number(raw)}{'%' if '%' in label else ''}"
    return _text(raw)


def _text(value):
    return " ".join(str(value).split())


def _plain_header_row(values):
    return (
        len(values) == 2
        and not any(_display_label(cell) or finite(cell.get("value"))
                    or date_value(cell.get("value")) for cell in values)
        and all(HEADER_ONLY.search(_text(cell["value"])) for cell in values)
    )
