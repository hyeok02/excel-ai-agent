"""Shared source-address and header normalization for record summaries."""
import re

from app.services.insights.narratives.narrative_values import reference


def _words(value):
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", str(value)).replace("_", " ")


def _range(sheet, cells):
    return reference(sheet, f"{cells[0]['cell']}:{cells[-1]['cell']}")
