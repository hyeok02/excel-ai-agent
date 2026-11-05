"""A table's own source line and metric definitions, quoted from its notes.

A card that says "천식 발작 경험 비율 3.6%" does not say whose rate it is or how
it is counted. Statistical tables usually state both under the table: a source
line ("DATA: Centers for Disease Control …", "출처: …") and footnotes that define
each measure ('"Asthma attack prevalence" represents children who …'). Both are
read here from the cited table's own note cells and quoted as written, never
translated or paraphrased. A footnote defines a card only when it quotes that
card's source label exactly; a note that names several measures, or none in
quotes, is not attached to any one of them.
"""
import re

from openpyxl.utils.cell import coordinate_to_tuple

from app.services.insights.narratives.narrative_values import reference
from app.services.insights.narratives.source_context import source_table_window
from app.services.insights.narratives.source_qualifications import _note_cells

_SOURCE = re.compile(r"^\s*(?:data(?:\s+source)?|sources?|출처|자료\s*출처|자료)\s*[:：]\s*(?P<text>\S.{2,400})$",
                     re.I | re.S)
_QUOTED = re.compile(r"[\"“”'‘’]([^\"“”'‘’]{2,80})[\"“”'‘’]")
_DEFINES = re.compile(r"\b(?:represents?|refers?\s+to|is\s+defined\s+as|means|measures?|is\s+the)\b|(?:란|이란|은|는)\s", re.I)
MAX_DEFINITION = 300


def source_annotations(context, item):
    """(source line, definition line, cited note cells) for one numeric card."""
    window = source_table_window(context, item)
    if window is None:
        return "", "", []
    name, first_row, next_row, first_col, next_col = window
    sheet = next((s for s in context.get("sheets", []) if isinstance(s, dict)
                  and str(s.get("name", "")).casefold() == name.casefold()), None)
    if sheet is None:
        return "", "", []
    labels = _labels(item)
    source = definition = ""
    refs = []
    for cell in _note_cells(sheet):
        try:
            row, col = coordinate_to_tuple(cell["cell"])
        except (KeyError, ValueError):
            continue
        value = cell.get("value")
        if not (first_row <= row < next_row and first_col <= col < next_col) or not isinstance(value, str):
            continue
        text = " ".join(value.split())
        if not source and (match := _SOURCE.match(text)):
            source = match["text"].rstrip()
            refs.append(reference(sheet["name"], cell["cell"]))
        elif not definition and labels and _defines(text, labels):
            definition = text.lstrip("*•- ").strip()
            refs.append(reference(sheet["name"], cell["cell"]))
    return source, definition, refs


def _labels(item):
    topic = str(getattr(item, "topic", "") or "")
    return {part.strip().casefold() for part in topic.split("·") if len(part.strip()) >= 3}


def _defines(text, labels):
    quoted = {quote.strip().casefold() for quote in _QUOTED.findall(text)}
    named = quoted & labels
    # One quoted measure, defined in the same note, and short enough to read.
    return len(quoted) == 1 and bool(named) and len(text) <= MAX_DEFINITION and bool(_DEFINES.search(text))
