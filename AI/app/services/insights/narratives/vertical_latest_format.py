"""Source period labels and complete short-series paths for recent changes."""
import re

from app.services.insights.facts.series_scalars import displayed_value, unit
from app.services.insights.narratives.narrative_values import direction_particle, finite, number, period, reference
from app.services.insights.narratives.series_path import series_shape
from app.services.insights.narratives.vertical_latest_series import _MONTHS

MAX_PATH = 240


def _period(record):
    original = record[1]["value"]
    if finite(original) or re.fullmatch(r"(?:19|20|21)\d{2}", str(original).strip()):
        return f"{record[0].year}년"
    if str(original).casefold().rstrip(".") in _MONTHS:
        return f"{record[0].year}년 {record[0].month}월"
    return period(original)


def _suffix(units):
    # "43.02%", not "43.02 %": a percent sign is written against its number.
    return "" if not units else units if units == "%" else f" {units}"


def _path(sheet, records, position, units):
    if not 3 <= len(records) <= MAX_PATH:
        return "", []
    cells = [record[2].get(position, {}) for record in records]
    if not all(finite(c.get("value")) for c in cells) or len({unit(c) for c in cells}) != 1:
        return "", []
    values = [displayed_value(c) for c in cells]
    labels = [_period(record) for record in records]
    texts = [f"{number(value)}{_suffix(units)}" for value in values]
    lines = []
    if len(records) > 4 and values[0] != values[-1]:
        # A latest-change card on a long series also states the whole period.
        delta = values[-1] - values[0]
        lines.append(f"전체 기간으로는 {labels[0]} {texts[0]}에서 {labels[-1]} {texts[-1]}{direction_particle(texts[-1])} "
                     f"{number(abs(delta))}{'%p' if units == '%' else _suffix(units)} "
                     f"{'증가' if delta > 0 else '감소'}했습니다.")
    if shape := series_shape(labels, values, texts):
        lines.append(shape)
    if not lines:
        return "", []
    text = "".join(f"\n{line}" for line in lines)
    evidence = []
    for source in ([record[1] for record in records], cells):
        ordered = sorted(source, key=lambda c: int(re.search(r"\d+$", c["cell"])[0]))
        evidence.append(reference(sheet, f"{ordered[0]['cell']}:{ordered[-1]['cell']}"))
    return text, evidence
