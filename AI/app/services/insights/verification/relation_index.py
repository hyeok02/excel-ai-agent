"""Retain source cell bindings instead of flattening a cited table into a bag."""
from dataclasses import dataclass
import re
from openpyxl.utils.cell import quote_sheetname

from app.services.insights.facts.fact_trends import date_value
from app.services.insights.verification.source_scalars import scalar


@dataclass(frozen=True)
class Observation:
    labels: tuple[str, ...]
    qualifiers: tuple[str, ...]
    value: str
    references: frozenset[str]
    period: str | None = None


def sheet_observations(sheet):
    from app.services.insights.verification.validation_index import normalize_reference
    name = str(sheet.get("name", ""))
    facts = sheet.get("business_facts", {})
    result = []

    def reference(cell):
        address = cell.get("cell") or cell.get("address")
        return normalize_reference(f"{quote_sheetname(name)}!{address}") if address else None

    def add_row(cells, headers=None):
        cells = [cell for cell in cells if isinstance(cell, dict)]
        raw = lambda cell: cell.get("cached_value") if cell.get("formula") else cell.get("value")
        texts = [str(raw(cell)) for cell in cells if raw(cell) not in (None, "")
                 and not scalar(raw(cell)) and not date_value(str(raw(cell)))]
        periods = [str(raw(cell)) for cell in cells if date_value(str(raw(cell)))]
        preceding = None
        bindings = []
        for cell in cells:
            value = raw(cell)
            if not scalar(value):
                if value not in (None, "") and not date_value(str(value)):
                    preceding = str(value)
                continue
            address = str(cell.get("cell") or cell.get("address", ""))
            column = re.sub(r"\d|\$", "", address)
            label = cell.get("label") or (headers or {}).get(column)
            labels = tuple(dict.fromkeys(str(item) for item in (label, preceding) if item))
            ref = reference(cell)
            if ref:
                bindings.append((labels, str(value), ref))
        bound_labels = {label for labels, _, _ in bindings for label in labels}
        qualifiers = tuple(text for text in texts if text not in bound_labels)
        for labels, value, ref in bindings:
            result.append(Observation(labels, qualifiers, value, frozenset({ref}),
                                      periods[0] if len(periods) == 1 else None))

    def add_rows(cells):
        grouped = {}
        for cell in cells:
            address = str(cell.get("cell") or cell.get("address", ""))
            grouped.setdefault(re.sub(r"\D", "", address), []).append(cell)
        headers = {}
        for _, row in sorted(grouped.items(), key=lambda item: int(item[0] or 0)):
            nonempty = [cell for cell in row if cell.get("value") not in (None, "")]
            if nonempty and all(not scalar(cell.get("value")) for cell in nonempty):
                headers = {re.sub(r"\d|\$", "", str(cell.get("cell") or cell.get("address", ""))):
                           str(cell["value"]) for cell in nonempty}
            else:
                add_row(row, headers)

    for key in ("selected_records", "time_series"):
        for record in facts.get(key, []):
            if isinstance(record, dict):
                add_rows(record.get("values", []))
    tables = facts.get("table_regions") or [{"rows": facts.get("table_rows", [])}]
    for table in tables:
        add_rows([cell for row in table.get("rows", []) for cell in row])
    for series in facts.get("horizontal_series", []):
        for point in series.get("points", []):
            ref = normalize_reference(f"{quote_sheetname(name)}!{point.get('value_cell')}")
            if ref and scalar(point.get("value")):
                result.append(Observation((str(series.get("metric", "")),),
                                          tuple(str(series[key]) for key in ("scope", "basis")
                                                if series.get(key)), str(point["value"]),
                                          frozenset({ref}), str(point.get("period") or "") or None))
    return list(dict.fromkeys(result))
