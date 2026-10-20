"""Resolve unit controls by source geometry, keeping parallel tables separate."""
import re

from app.agent.query.metric_observations import _column, _human_label
from app.agent.query.trend_row_metadata import UNIT_HEADERS


def explicit_row_settings(observation, currency_parser, magnitude_parser, kinds=None):
    values, references = {}, []
    for header in observation.unit_context:
        kind = UNIT_HEADERS.get(str(header.value).strip().casefold())
        if kind is None or kinds is not None and kind not in kinds:
            continue
        cell = next((cell for cell in observation.unit_context if cell != header
                     and _column(cell) == _column(header)), None)
        parser = currency_parser if kind == "currency" else magnitude_parser
        parsed = _unambiguous_control(str(cell.value), parser) if cell else ""
        if not parsed or kind in values and values[kind] != parsed:
            return None, tuple(references)
        values[kind] = parsed
        references.extend((header, cell))
    return values, tuple(dict.fromkeys(references))


def _unambiguous_control(value, parser):
    if len(value) > 250 or re.search(r"\b(?:not|except|excluding)\b|아닌|제외", value, re.I):
        return ""
    parts = re.split(r"[/,;]|\b(?:or|and)\b|또는|및", value, flags=re.I)
    if len(parts) > 1 and any(not parser(part) for part in parts):
        return ""
    words = value.split()
    choices = {parser(value), *(parser(part) for part in parts)}
    choices.update(parser(" ".join(words[start:start + size]))
                   for size in (1, 2, 3) for start in range(len(words)))
    choices.discard("")
    return next(iter(choices)) if len(choices) == 1 else ""


def source_settings(rows, observation, currency_parser, magnitude_parser):
    by_row = {row.row_number: row for row in rows}
    value_row = int(re.search(r"\d+", observation.value.address)[0])
    value_line = by_row.get(value_row)
    right = min((_column(cell) for cell in value_line.cells
                 if _column(cell) > _column(observation.value) and _human_label(cell)),
                default=16_385) if value_line else 16_385
    groups = {"currency": [], "magnitude": []}
    for row in rows:
        if row.row_number >= value_row:
            continue
        below = by_row.get(row.row_number + 1)
        if below is None:
            continue
        for cell in row.cells:
            if _column(cell) >= right:
                continue
            label = str(cell.value or "").strip().casefold()
            kind = ("currency" if label in {"currency", "통화"} else
                    "magnitude" if label in {"magnitude", "금액 단위"} else None)
            if kind is None:
                continue
            source = next((other for other in below.cells if _column(other) == _column(cell)), None)
            if source is None:
                continue
            parsed = (currency_parser if kind == "currency" else magnitude_parser)(str(source.value))
            if parsed:
                groups[kind].append((row.row_number, _column(cell), parsed, cell, source))
    values, references = {}, []
    for kind, candidates in groups.items():
        if not candidates:
            values[kind] = ""
            continue
        nearest_row = max(item[0] for item in candidates)
        current = [item for item in candidates if item[0] == nearest_row]
        # A single report-level control may be centered above several values.
        # Repeated controls delimit parallel report blocks; never borrow the
        # control belonging to the next block on the right.
        eligible = current if len(current) == 1 else [item for item in current
                                                     if item[1] <= _column(observation.value)]
        if not eligible:
            values[kind] = ""
            continue
        chosen = max(eligible, key=lambda item: item[1])
        values[kind] = chosen[2]
        references.extend(chosen[3:])
    return values.get("currency", ""), values.get("magnitude", ""), references
