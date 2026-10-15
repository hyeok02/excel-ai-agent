"""Bind entity identity before choosing dates or values."""
import re
from dataclasses import replace
from app.agent.query.metric_observations import _normal

def _bind_entity_scope(question, observations, rows, named_sheets):
    """Bind named entities before period selection, never after picking latest."""
    metric_labels = {str(item.label.value).casefold() for item in observations}
    entities = []
    for name in re.findall(r"([A-Za-z0-9_가-힣][A-Za-z0-9_가-힣 .,&-]*?)의\s", question):
        name = re.split(r"(?:에서|시트|파일|내)\s+", name)[-1].strip()
        if not name or any(word in name for word in ("분기", "연도", "날짜", "기간", "최근", "최신")):
            continue
        if any(name.casefold() in label for label in metric_labels):
            continue
        if any(name.casefold() in {sheet.casefold(), f"{sheet.casefold()} 시트"} for sheet in named_sheets):
            continue
        entities.append(name)
    if not entities:
        # Explicit English company names are bound by their appearance in a
        # local source title/record, excluding metric and operation vocabulary.
        from app.agent.tools.workbook_metric_vocabulary import GENERIC_METRIC_WORDS

        source_entities = []
        for item in observations:
            source_entities.extend(item.entity_cells)
        for row in rows:
            if row.row_number < 20:
                source_entities.extend(cell for cell in row.cells if isinstance(cell.value, str)
                                       and not any(str(cell.value).casefold() in label for label in metric_labels))
        source_names = [str(cell.value) for cell in source_entities
                        if len(str(cell.value)) < 100 and not str(cell.value).casefold() in GENERIC_METRIC_WORDS
                        and _source_entity_mentioned(str(cell.value), question, metric_labels)]
        entities = list(dict.fromkeys(source_names))
    if not entities:
        return observations
    bound = []
    for item in observations:
        local = [*item.entity_cells]
        if not local:
            label_row = int(re.search(r"\d+", item.label.address)[0])
            local = [cell for row in rows if row.sheet_name == item.value.sheet_name
                     and row.row_number < label_row for cell in row.cells
                     if isinstance(cell.value, str)]
        matched = [cell for entity in entities for cell in local
                   if entity.casefold() in str(cell.value).casefold()
                   or _source_entity_mentioned(str(cell.value), entity, set())]
        matched = [cell for cell in matched if not _closer_peer_entity(cell, local)]
        if matched:
            # One concise source identifier proves the binding; repeating the
            # same ticker or copying a business-description paragraph does not.
            shortest = min(matched, key=lambda cell: len(str(cell.value)))
            bound.append(replace(item, entity_cells=(shortest,)))
    return bound or None

def _closer_peer_entity(matched, local):
    """Repeated entity-caption structure closes the preceding entity's scope."""
    column = re.sub(r"\d", "", matched.address)
    number = int(re.search(r"\d+", matched.address)[0])
    words = _normal(str(matched.value)).split()
    if len(words) < 2:
        return False
    suffix = words[-1]
    for candidate in local:
        peer = _normal(str(candidate.value)).split()
        if (re.sub(r"\d", "", candidate.address) == column
                and int(re.search(r"\d+", candidate.address)[0]) > number
                and len(peer) == len(words) and peer[-1] == suffix and peer != words):
            return True
    return False

def _source_entity_mentioned(source, question, labels):
    from app.agent.tools.workbook_metric_vocabulary import GENERIC_METRIC_WORDS

    words = [word for word in re.findall(r"[a-z][a-z0-9]+", source.casefold())
             if word not in GENERIC_METRIC_WORDS | {"inc", "llc", "ltd", "corp", "corporation", "fy"}]
    if not words or any(_normal(source) == _normal(label) for label in labels):
        return False
    if len(words) == 1 and len(words[0]) < 3:
        return False
    return all(re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", question, re.I)
               for word in words)
