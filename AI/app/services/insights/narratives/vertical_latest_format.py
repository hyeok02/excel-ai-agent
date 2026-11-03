"""Source period labels and complete short-series paths for recent changes."""
import re

from app.services.insights.facts.series_scalars import displayed_value, unit
from app.services.insights.narratives.narrative_values import finite, number, period, reference
from app.services.insights.narratives.series_path import path_direction
from app.services.insights.narratives.vertical_latest_series import _MONTHS


def _period(record):
    original = record[1]["value"]
    if finite(original) or re.fullmatch(r"(?:19|20|21)\d{2}", str(original).strip()):
        return f"{record[0].year}년"
    if str(original).casefold().rstrip(".") in _MONTHS:
        return f"{record[0].year}년 {record[0].month}월"
    return period(original)


def _suffix(units):
    return f" {units}" if units else ""


def _path(sheet, records, position, units):
    if not 3 <= len(records) <= 12:
        return "", []
    cells = [record[2].get(position, {}) for record in records]
    if not all(finite(c.get("value")) for c in cells) or len({unit(c) for c in cells}) != 1:
        return "", []
    values = [displayed_value(c) for c in cells]
    indexes = sorted({0, len(records) // 3, 2 * len(records) // 3, len(records) - 1})
    timeline = " → ".join(f"{_period(records[i])} {number(values[i])}{_suffix(units)}" for i in indexes)
    coverage = "기간별 기록" if len(indexes) == len(records) else "주요 시점의 기록"
    text = f" {coverage}은 {timeline}입니다. {path_direction(values)}"
    evidence = []
    for source in ([record[1] for record in records], cells):
        ordered = sorted(source, key=lambda c: int(re.search(r"\d+$", c["cell"])[0]))
        evidence.append(reference(sheet, f"{ordered[0]['cell']}:{ordered[-1]['cell']}"))
    return text, evidence
