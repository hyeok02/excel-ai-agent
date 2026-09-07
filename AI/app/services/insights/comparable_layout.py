"""Recognize comparable-transaction tables split into worksheet regions."""
import math
import re

from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

COMPARABLE = re.compile(r"comparab.*transaction|transaction.*comparab|비교.*거래", re.I)
TARGET_NAME = re.compile(r"target.*(?:issuer.*)?name|피인수.*(?:기업|대상).*이름", re.I)
TRANSACTION_ID = re.compile(r"(?:transaction|deal).*(?:\bid\b|ids\b)|거래.*(?:id|아이디)", re.I)
FOCUS_ID = re.compile(r"(?:focus|subject|base).*(?:transaction|deal)?.*(?:\bid\b|ids\b)|기준.*거래.*(?:id|아이디)", re.I)
PROVIDER_KEY = re.compile(r"^(?:SP[A-Z0-9_]+|NA)$", re.I)
STATISTIC = {
    "high": re.compile(r"^(?:high|max|maximum|최대)$", re.I),
    "median": re.compile(r"^(?:median|중앙값)$", re.I),
    "low": re.compile(r"^(?:low|min|minimum|최소)$", re.I),
    "average": re.compile(r"^(?:average|mean|평균)$", re.I),
}


def comparable_layout(sheet_name, regions):
    cells = _cells(regions)
    scope = " ".join([sheet_name, *(str(cell["value"]) for cell in cells.values())])
    if not cells or not COMPARABLE.search(scope):
        return None
    rows = _rows(cells)
    header = _find_header(rows)
    if not header:
        return None
    header_row, metrics, name_column, id_column = header
    if not {"ebitda_multiple", "transaction_value"} <= metrics.keys():
        return None
    stats = _statistics(rows, header_row, [item[0] for item in metrics.values()])
    if not stats:
        return None
    first_stat, last_stat = min(stats.values()), max(stats.values())
    peers = _peer_rows(rows, header_row, first_stat, name_column, metrics)
    declared, focus_id = _focus_id(rows, header_row, id_column)
    subject = _subject_row(rows, header_row, last_stat, name_column, id_column,
                           metrics, declared, focus_id)
    if len(peers) < 3 or subject is None:
        return None
    return {"cells": cells, "rows": rows, "headers": metrics, "peers": peers,
            "name_column": name_column, "subject": subject, "median_row": stats["median"]}
def metric_kind(label):
    normalized = " ".join(label.casefold().split())
    if "ebitda" in normalized and ("value" in normalized or "ev" in normalized):
        if "(x)" in normalized or "multiple" in normalized or "/" in normalized:
            return "ebitda_multiple", 2 if "transaction" in normalized else 1
    if "total transaction value" in normalized or "총 거래가치" in normalized:
        return "transaction_value", 2
    if "transaction value" in normalized and not any(
        word in normalized for word in ("per share", "ebit", "ebitda")
    ):
        return "transaction_value", 1
    return None, 0
def finite(cell):
    value = cell.get("value") if isinstance(cell, dict) else None
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
def _cells(regions):
    result = {}
    for region in regions:
        for row in region.get("analysis_rows") or region.get("preview_rows", []):
            for cell in row:
                value = cell.get("cached_value") if cell.get("formula") else cell.get("value")
                if cell.get("address") and value not in (None, ""):
                    result[str(cell["address"])] = {
                        "cell": str(cell["address"]), "value": value,
                        "number_format": cell.get("number_format"),
                    }
    return result
def _rows(cells):
    result = {}
    for cell in cells.values():
        name, row = coordinate_from_string(cell["cell"])
        result.setdefault(row, {})[column_index_from_string(name)] = cell
    return result
def _find_header(rows):
    candidates = []
    for row_number, row in rows.items():
        metrics, name_column, id_column = {}, None, None
        for column, cell in row.items():
            label = " ".join(str(cell["value"]).split())
            kind, priority = metric_kind(label)
            if kind and (kind not in metrics or priority > metrics[kind][0]):
                metrics[kind] = (priority, column, cell)
            if TARGET_NAME.search(label):
                name_column = column
            if TRANSACTION_ID.search(label):
                id_column = column
        if metrics and name_column:
            candidates.append((len(metrics), sum(item[0] for item in metrics.values()),
                               -row_number, row_number, metrics, name_column, id_column))
    if not candidates:
        return None
    *_, row_number, metrics, name_column, id_column = max(candidates)
    return row_number, {key: value[1:] for key, value in metrics.items()}, name_column, id_column
def _statistics(rows, header_row, metric_columns):
    matches = []
    for row_number in sorted(row for row in rows if row > header_row):
        for column, cell in rows[row_number].items():
            label = next((name for name, pattern in STATISTIC.items()
                          if pattern.fullmatch(" ".join(str(cell["value"]).split()))), None)
            if label:
                matches.append((row_number, column, label))
    for start, label_column, _ in matches:
        group = [(row, label) for row, column, label in matches
                 if column == label_column and start <= row <= start + 5]
        row_numbers = [row for row, _ in group]
        if (len({label for _, label in group}) >= 3
                and any(label == "median" for _, label in group)
                and row_numbers == list(range(min(row_numbers), max(row_numbers) + 1))
                and any(all(finite(rows[row].get(column)) for row in row_numbers)
                        for column in metric_columns)):
            return {label: row for row, label in group}
    return {}
def _peer_rows(rows, header_row, first_stat, name_column, metrics):
    columns = [value[0] for value in metrics.values()]
    return [row for row in sorted(rows) if header_row < row < first_stat
            and rows[row].get(name_column)
            and not PROVIDER_KEY.fullmatch(str(rows[row][name_column]["value"]).strip())
            and any(finite(rows[row].get(column)) for column in columns)]
def _focus_id(rows, header_row, id_column):
    identifiers = {str(row[id_column]["value"]) for number, row in rows.items()
                   if id_column and number > header_row and row.get(id_column)}
    declared = False
    for row in rows.values():
        for column, cell in row.items():
            if FOCUS_ID.search(str(cell["value"])):
                declared = True
                choices = [item for item in row.items() if item[0] != column
                           and str(item[1]["value"]) in identifiers]
                if choices:
                    found = min(choices, key=lambda item: abs(item[0] - column))
                    return True, str(found[1]["value"])
    return declared, None
def _subject_row(rows, header_row, last_stat, name_column, id_column, metrics,
                 focus_declared, focus_id):
    columns = [value[0] for value in metrics.values()]
    usable = lambda row: (rows[row].get(name_column)
                          and any(finite(rows[row].get(column)) for column in columns))
    if focus_declared:
        matched = [row for row in rows if row > header_row and usable(row)
                   and str(rows[row].get(id_column, {}).get("value", "")) == focus_id]
        return min(matched) if matched else None
    fallback = [row for row in rows if last_stat < row <= last_stat + 4 and usable(row)]
    return fallback[0] if len(fallback) == 1 else None
