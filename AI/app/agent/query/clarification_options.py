"""Reproducible options bound to the current workbook and source identities."""
from dataclasses import asdict
from hashlib import sha256
import json
import re

from openpyxl.utils.cell import coordinate_from_string

from app.agent.query.clarification_models import SourceClarificationOption


def source_clarification_options(question, candidates, summary, index):
    digest = getattr(index, "source_digest", "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or not 2 <= len(question) <= 1000:
        return []
    if summary is None:
        return []
    cells = {cell.reference: cell for row in index.rows for cell in row.cells}
    sheets = {sheet.name: sheet for sheet in summary.sheets}
    options = []
    for candidate in candidates[:6]:
        if not 2 <= len(candidate.followup) <= 1000 or not candidate.cells:
            continue
        if not all(_visible(cell, cells, sheets) for cell in candidate.cells):
            continue
        source = asdict(candidate)
        source["cells"] = sorted(source["cells"], key=lambda cell: (cell["sheet_name"], cell["address"]))
        identity = {"source_digest": digest, "source_question": question, "candidate": source}
        encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, default=str).encode()
        options.append(SourceClarificationOption(
            id=sha256(encoded).hexdigest(), label=candidate.label[:200],
            scope=candidate.scope[:200], details=candidate.details[:1000], question=candidate.followup,
        ))
    return options


def _visible(cell, indexed, sheets):
    sheet = sheets.get(cell.sheet_name)
    if sheet is None or indexed.get(cell.reference) != cell:
        return False
    column, row = coordinate_from_string(cell.address)
    return not any(row in region.hidden_rows or column in region.hidden_columns for region in sheet.regions)
