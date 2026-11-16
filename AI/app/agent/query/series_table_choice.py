"""One series stated by several tables: the question's other words may name the table.

"전력 부문 배출량" names the series 'Electricity supply total' that the gas tables 1.2-1.5
all state. A remaining word that reads as one table's title ("메탄" → the methane table)
picks it; with no such word the report's own order decides, as on its cards, and the table
is named in the answer. Two words naming different tables leave no single answer.
"""
import asyncio
import re

from app.agent.query.references import normalize_reference

MAX_TITLE = 200


def table_choice(question_words, word, items, cells, resolver):
    labels = [_label(item, cells) for item in items]
    if None in labels or len(set(labels)) != len(labels):
        return None  # two readings inside one table cannot be told apart by its title
    used = set(word.split())
    rest = [other for other in question_words if not used & set(other.split())]
    readings = asyncio.run(_read(resolver, rest, labels)) if rest else []
    named = {result.candidate_id for result in readings
             if result.status == "resolved" and type(result.candidate_id) is int
             and 0 <= result.candidate_id < len(items)}
    if len(named - {0}) > 1:
        return None
    chosen = next(iter(named - {0}), 0)
    return items[chosen], labels[chosen], [label for number, label in enumerate(labels) if number != chosen]


def _label(item, cells):
    for reference in item.evidence:
        cell = cells.get(normalize_reference(reference))
        if cell is not None and isinstance(cell.value, str) and re.search(r"[^\W\d_]", cell.value):
            return f"{cell.sheet_name} — {cell.value.strip()[:MAX_TITLE]}"
    return None


async def _read(resolver, words, labels):
    return await asyncio.gather(*(resolver.resolve(word, "table title", labels) for word in words))
