"""Summarise record tables by their full distribution instead of reciting rows."""
from app.services.insights.facts.categorical_columns import (
    category_column, header_index, header_like, measurable,
)
from app.services.insights.narratives.categorical_dates import (
    counted_range, date_spread,
)
from app.services.insights.narratives.categorical_scope import scope_prefix
from app.services.insights.display.glossary import readable, translate
from app.services.insights.narratives.narrative_values import (
    insight, number, reference, subject_particle,
)
from app.services.insights.narratives.topic_labels import source_topic
from app.services.insights.facts.sheet_scope import narrative_sheet_groups
from app.services.insights.facts.table_inputs import narrative_regions

MIN_RECORDS = 5
MAX_LISTED = 4


def categorical_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    candidates = _candidates(primary) or _candidates(comparisons)
    if not candidates:
        return [], ""
    first = min(candidate[0] for candidate in candidates)
    _, items, overview, _ = max(
        (candidate for candidate in candidates if candidate[0] == first),
        key=lambda candidate: candidate[3],
    )
    return items[:5], overview


def _candidates(sheets):
    results = []
    qualify = len(sheets) > 1
    for source_order, sheet in sheets:
        facts = sheet.get("business_facts", {})
        carried, heading, heading_cell = None, "", None
        for region in narrative_regions(facts):
            if region.get("rows_complete") is False:
                carried, heading, heading_cell = None, "", None
                continue
            rows = region.get("rows", [])
            report = _region_report(
                str(sheet.get("name", "")), rows, heading, carried, heading_cell,
                qualify,
            )
            if report:
                results.append((source_order, *report))
            carried = rows[-1] if rows and header_like(rows[-1]) else carried
            if caption := _heading(rows):
                heading, heading_cell = caption, rows[0][0]
    return results


def _heading(rows):
    """A table announces what it records in a caption of its own, above it."""
    if len(rows) != 1 or len(rows[0]) != 1:
        return ""
    return _title(rows[0][0].get("value"))


def _region_report(sheet, rows, title, carried=None, heading_cell=None, qualify=False):
    index = header_index(rows)
    header, records = (rows[index], rows[index + 1:]) if index is not None else (
        carried, rows
    )
    if header is None or len(records) < MIN_RECORDS:
        return None
    if measurable(header, records):
        return None
    category = category_column(header, records)
    if not category:
        return None
    name, counts, cells = category
    total = sum(count for _, count in counts)
    top_value, top_count = counts[0]
    kind = readable(_title(title) or name)
    header_ref = next((reference(sheet, cell["cell"]) for cell in header
                       if _flat(cell.get("value")) == _flat(name)), None)
    cited = [*([header_ref] if header_ref else []), *counted_range(sheet, cells)]
    if heading_cell and heading_cell.get("cell") and _title(title):
        cited.insert(0, reference(sheet, heading_cell["cell"]))
    topic = source_topic(title) if heading_cell else source_topic(name)
    share = number(round(top_count / total * 100, 1))
    following = ", ".join(f"{translate(value) or value} {number(count)}건"
                          for value, count in counts[1:3])
    tail = f", 이어서 {following}입니다" if following else "입니다"
    headline = readable(top_value)
    items = [insight(
        f"{kind} 구성",
        f"{scope_prefix(sheet, qualify)}‘{headline}’{subject_particle(headline)} "
        f"{number(total)}건 중 {number(top_count)}건({share}%)으로 가장 많고{tail}.",
        cited, topic=topic,
    )]
    listed = _distribution(name, counts, total)
    if listed:
        items.append(insight(f"{readable(name)} 분포", listed,
                             cited, topic=source_topic(name)))
    dated = date_spread(sheet, header, records)
    if dated:
        items.append(dated)
    return items, items[0].fact, total + (10 if dated else 0)


def _title(value):
    raw = str(value or "").strip()
    text = _flat(raw)
    return raw if 2 <= len(text) <= 40 and not text.replace(".", "").isdigit() else ""


def _distribution(name, counts, total):
    if len(counts) < 2:
        return ""
    parts = [f"{translate(value) or value} {number(count)}건"
             for value, count in counts[:MAX_LISTED]]
    rest = len(counts) - len(parts)
    tail = f", 그 밖에 {number(rest)}개" if rest > 0 else ""
    return (f"‘{readable(name)}’ 항목은 {len(counts)}가지로 나뉩니다. "
            f"{', '.join(parts)}{tail}입니다.")


def _flat(value):
    return " ".join(str(value or "").split())
