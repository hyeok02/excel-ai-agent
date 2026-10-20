"""Typed source observations and label/coordinate matching primitives."""
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from app.agent.query.comparison_scope import column_from_address, column_number
from app.agent.query.index import IndexedCell
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.search_terms import SEMANTIC_ALIASES
_DATE_HEADER = re.compile(r"\b(?:date|period|year|as\s+of)\b|날짜|일자|기준일|기준월|기간|연도", re.I)
_ABSENT = {"na", "n/a", "n.a.", "-", "#pend", "#n/a"}
_CODE = re.compile(r"^[A-Z][A-Z0-9]*_[A-Z0-9_]+$")
_METRIC_MODIFIERS = re.compile(r"\b(?:latest|actual|actuals|annual|total)\b|\([^)]*\)", re.I)



@dataclass(frozen=True)
class MetricObservation:
    label: IndexedCell
    value: IndexedCell
    period: datetime
    period_cell: IndexedCell
    grain: str | None
    scenario: str | None
    context_cells: tuple[IndexedCell, ...]
    entity_cells: tuple[IndexedCell, ...] = ()
    unit_context: tuple[IndexedCell, ...] = ()

def metric_label_matches(label: str, question: str) -> bool:
    normalized = _normal(label)
    query = _normal(question)
    if not normalized or _DATE_HEADER.search(label):
        return False
    if re.search(r"(?<!\w)" + re.escape(normalized) + r"(?![a-z0-9])", query):
        return True
    simple = _normal(_METRIC_MODIFIERS.sub(" ", label))
    if not simple:
        return False
    # Semantic aliases only apply to complete source metric names. A Revenue
    # match never admits Revenue Growth, Revenue / Employee or TEV / Revenue.
    for concept, aliases in SEMANTIC_ALIASES.items():
        names = {_normal(value) for value in (concept, *aliases)}
        if simple not in names:
            continue
        if any((_korean_metric_in_question(name, question) if re.search(r"[가-힣]", name)
                else re.search(r"(?<!\w)" + re.escape(name) + r"(?![a-z0-9])", query))
               for name in names):
            return True
    return bool(re.search(r"(?<!\w)" + re.escape(simple) + r"(?![a-z0-9])", query))

def _korean_metric_in_question(name, question):
    return bool(re.search(
        r"(?<![가-힣])(?:총|전체)?" + re.escape(name)
        + r"(?:액|수)?(?:은|는|을|를|이|가|의|과|와|도|만)?(?=$|[^가-힣])", question,
    ))

def _sheet_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.sheet_name].append(row)
    return {name: sorted(items, key=lambda row: row.row_number) for name, items in grouped.items()}

def _human_label(cell):
    value = cell.value
    return (isinstance(value, str) and 1 < len(value.strip()) < 160
            and value.casefold().strip() not in _ABSENT and not _CODE.fullmatch(value)
            and source_period(value) is None and bool(re.search(r"[a-z가-힣]", value, re.I)))

def _text_in_question(value, question):
    # Full source IDs may contain corporate punctuation or suffixes. Match the
    # name's distinct words; a one-word category like USA is not a row identity.
    source = _normal(value)
    query = _normal(question)
    words = [word for word in source.split() if word not in {"inc", "llc", "ltd", "corp", "corporation"}]
    return len(words) >= 2 and " ".join(words) in query or len(source) >= 5 and source in query

def _normal(value):
    return " ".join(re.findall(r"[a-z0-9가-힣]+", value.casefold()))

def _column(cell):
    return column_number(column_from_address(cell.address))

def _numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
