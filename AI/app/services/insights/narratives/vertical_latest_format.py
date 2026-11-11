"""Source period labels and complete short-series paths for recent changes."""
import re

from app.services.insights.facts.series_scalars import displayed_text, displayed_value, unit
from app.services.insights.narratives.change_sentence import change_sentence
from app.services.insights.narratives.narrative_values import finite, number, period, reference
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
    """(whole-period sentence, shape line, evidence) when every period's value is readable."""
    if not 3 <= len(records) <= MAX_PATH:
        return "", "", []
    cells = [record[2].get(position, {}) for record in records]
    if not all(finite(c.get("value")) for c in cells) or len({unit(c) for c in cells}) != 1:
        return "", "", []
    values = [displayed_value(c) for c in cells]
    labels = [_period(record) for record in records]
    texts = [f"{displayed_text(c, value)}{_suffix(units)}" for c, value in zip(cells, values)]
    whole = change_sentence(f"{labels[0]} {texts[0]}", f"{labels[-1]} {texts[-1]}", values[0], values[-1],
                            _suffix(units))
    evidence = []
    for source in ([record[1] for record in records], cells):
        ordered = sorted(source, key=lambda c: int(re.search(r"\d+$", c["cell"])[0]))
        evidence.append(reference(sheet, f"{ordered[0]['cell']}:{ordered[-1]['cell']}"))
    return whole, series_shape(labels, values, texts), evidence
