"""Build bounded comparable-transaction facts from a detected table layout.

Price level is judged only by multiples (price per unit of earnings); the
transaction amount is reported as deal size. Industry, buyer and announcement
date come from the same row, so caveats are stated from source values.
"""
import re
from collections import Counter
from datetime import date, datetime

from app.services.insights.facts.comparable_layout import comparable_layout
from app.services.insights.facts.comparable_metrics import (
    _at, _range, _reference, column_metric, derived_multiples, source_multiples,
)


def extract_comparable_transactions(sheet_name, regions):
    layout = comparable_layout(sheet_name, regions)
    if not layout:
        return None
    rows = layout["rows"]
    subject_cell = rows[layout["subject"]][layout["name_column"]]
    multiples = source_multiples(sheet_name, layout)
    multiples += derived_multiples(sheet_name, layout, {item["basis"] for item in multiples})
    sizes = sorted((item for item in layout["columns"] if item["role"] == "size"),
                   key=lambda item: -item["priority"])
    size = next((metric for item in sizes if (metric := column_metric(sheet_name, layout, item, "size"))), None)
    metrics = [*multiples, *([size] if size else [])]
    if not metrics:
        return None
    subject_reference = _reference(sheet_name, subject_cell["cell"])
    for metric in metrics:
        metric["evidence"].insert(1, subject_reference)
    return {
        "subject": str(subject_cell["value"]).strip(),
        "subject_cell": subject_cell["cell"],
        "peer_count": len(layout["peers"]),
        "peer_name_range": _range(sheet_name, layout["name_column"], layout["peers"]),
        "metrics": metrics,
        "buyer": _subject_text(layout, "buyer"),
        "announced": _subject_date(layout),
        "industry": _industry(sheet_name, layout),
    }


def _subject_text(layout, role):
    for item in layout["columns"]:
        cell = _at(layout, item["column"], layout["subject"]) if item["role"] == role else None
        if cell and isinstance(cell["value"], str) and cell["value"].strip():
            return " ".join(cell["value"].split())
    return None


def _subject_date(layout):
    for item in layout["columns"]:
        cell = _at(layout, item["column"], layout["subject"]) if item["role"] == "announced" else None
        value = cell["value"] if cell else None
        if isinstance(value, (date, datetime)):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+)?", value.strip()):
            return value.strip()[:10]
    return None


def _industry(sheet, layout):
    """The most specific industry column: the one that separates peers most."""
    options = []
    for item in layout["columns"]:
        if item["role"] != "industry":
            continue
        subject = _at(layout, item["column"], layout["subject"])
        peers = [cell["value"].strip() for row in layout["peers"]
                 if (cell := _at(layout, item["column"], row)) and isinstance(cell["value"], str)
                 and cell["value"].strip()]
        if subject and isinstance(subject["value"], str) and peers:
            options.append((len(set(peers)), item, subject, peers))
    if not options:
        return None
    _, item, subject, peers = max(options, key=lambda option: option[0])
    return {"subject": subject["value"].strip(), "peers": Counter(peers).most_common(),
            "evidence": [_reference(sheet, subject["cell"]),
                         _range(sheet, item["column"], layout["peers"])]}
