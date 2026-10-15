"""Reject unsupported targets instead of dropping their qualifiers."""
import re
from app.agent.query.metric_observations import _normal

def _scope_references(question, observations, rows, named_sheets):
    references = []
    if not _english_scope_supported(question, observations, rows):
        return None
    for name in re.findall(r"([A-Za-z0-9_가-힣][A-Za-z0-9_가-힣 .,&-]*?)의\s", question):
        name = re.split(r"(?:에서|시트|파일|내)\s+", name)[-1].strip()
        if any(name.casefold() in {sheet.casefold(), f"{sheet.casefold()} 시트"} for sheet in named_sheets):
            continue
        # Phrases such as "같은 날짜 종료 분기의" are period qualifiers,
        # not corporate/entity names.
        if any(word in name for word in ("분기", "연도", "날짜", "기간", "최근", "최신")):
            continue
        if any(name.casefold() in str(item.label.value).casefold() for item in observations):
            continue
        selected_sheets = {item.value.sheet_name for item in observations}
        matches = [cell for row in rows if row.sheet_name in selected_sheets for cell in row.cells
                   if isinstance(cell.value, str) and name.casefold() in cell.value.casefold()
                   and (row.row_number < 50 or cell in [entity for item in observations for entity in item.entity_cells])]
        if not matches:
            return None
        references.append(min(matches, key=lambda cell: len(str(cell.value))))
    return references

def _multiple_named_metrics(question, observations):
    query = _normal(question)
    labels = {str(item.label.value) for item in observations}
    spans = []
    for label in sorted(labels, key=lambda value: -len(_normal(value))):
        normalized = _normal(label)
        for match in re.finditer(re.escape(normalized), query):
            if not any(match.start() < end and start < match.end() for start, end, _ in spans):
                spans.append((match.start(), match.end(), normalized))
    return len({label for _, _, label in spans}) > 1

def _english_scope_supported(question, observations, rows):
    from app.agent.tools.workbook_metric_vocabulary import GENERIC_METRIC_WORDS

    generic = GENERIC_METRIC_WORDS | {
        "year", "years", "fiscal", "fy", "quarter", "quarterly", "annual", "month", "monthly",
        "actual", "actuals", "estimate", "estimates", "forecast", "budget", "ended", "ending",
        "date", "dates", "period", "periods", "as", "same", "with", "versus", "vs", "between",
        "growth", "rate", "percentage", "percent", "difference", "delta", "unit", "units",
        "amounts", "both", "each", "respectively", "also", "last", "most", "inc", "llc", "ltd",
    }
    supported = " ".join(str(cell.value) for row in rows for cell in row.cells
                         if row.row_number < 50 or cell in [item.label for item in observations]
                         or cell in [entity for item in observations for entity in item.entity_cells])
    supported += " " + " ".join(row.sheet_name for row in rows)
    words = set(re.findall(r"[a-z][a-z0-9_]+", question.casefold()))
    return all(word in generic or word in supported.casefold() for word in words)
