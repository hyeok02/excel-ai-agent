"""Exact, bounded distinct tuple counts with explicit incomplete-row exclusion."""
from app.agent.query.formula_resolution_values import EXCEL_ERRORS
from app.agent.query.tabular_filters import finite_number
from app.agent.query.tabular_numeric import _unit_identity
from app.agent.query.excel_number_formats import parse_number_format

MAX_DISTINCT_KEYS = 100000
MAX_DISTINCT_CHARACTERS = 8000000


class DistinctState:
    def __init__(self, columns):
        self.columns = columns
        self.keys = self.characters = 0
        self.units = {}

    def add(self, group, row, typed_key):
        parts, incomplete = [], False
        for key in self.columns:
            value, style = row.values.get(key), row.number_formats.get(key, "General")
            if value is None and row.formulas.get(key):
                return False
            if isinstance(value, str) and value.strip().upper() in EXCEL_ERRORS:
                return False
            if value is None or isinstance(value, str) and not value.strip():
                incomplete = True
                continue
            part = typed_key(value, style)
            if part is None:
                return False
            if finite_number(value):
                unit = _unit_identity(parse_number_format(style))
                if key in self.units and self.units[key] != unit:
                    return False
                self.units[key] = unit
            parts.append(part[0])
        if incomplete:
            group.skipped += 1
            return True
        identity = tuple(parts)
        if identity in group.distinct:
            return True
        characters = len(repr(identity))
        if self.keys >= MAX_DISTINCT_KEYS or self.characters + characters > MAX_DISTINCT_CHARACTERS:
            return False
        self.keys += 1
        self.characters += characters
        group.distinct.add(identity)
        return True
