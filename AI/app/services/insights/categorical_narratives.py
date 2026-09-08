"""Summarise record tables by counting, not by reading rows back to the user.

Lists of events, applications or people carry no measured series, so the trend
and table narratives find nothing and fall back to reciting a row. What such a
table actually says is how its records are distributed.
"""
from app.services.insights.categorical_columns import (
    category_column, date_column, header_index, header_like, measurable,
)
from app.services.insights.glossary import readable, translate
from app.services.insights.narrative_values import (
    insight, number, period, reference, subject_particle,
)
from app.services.insights.sheet_scope import narrative_sheet_groups
from app.services.insights.table_inputs import narrative_regions

MIN_RECORDS = 5
MAX_EVIDENCE = 10
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
    for source_order, sheet in sheets:
        facts = sheet.get("business_facts", {})
        carried, heading = None, ""
        for region in narrative_regions(facts):
            rows = region.get("rows", [])
            report = _region_report(
                str(sheet.get("name", "")), rows, heading, carried,
            )
            if report:
                results.append((source_order, *report))
            carried = rows[-1] if rows and header_like(rows[-1]) else carried
            heading = _heading(rows) or heading
    return results


def _heading(rows):
    """A table announces what it records in a caption of its own, above it."""
    if len(rows) != 1 or len(rows[0]) != 1:
        return ""
    return _title(rows[0][0].get("value"))


def _region_report(sheet, rows, title, carried=None):
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
    share = number(round(top_count / total * 100, 1))
    following = ", ".join(f"{translate(value) or value} {number(count)}건"
                          for value, count in counts[1:3])
    tail = f", 이어서 {following}입니다" if following else "입니다"
    headline = readable(top_value)
    items = [insight(
        f"{kind} 구성",
        f"‘{headline}’{subject_particle(headline)} {number(total)}건 중 "
        f"{number(top_count)}건({share}%)으로 가장 많고{tail}.",
        _evidence(sheet, cells),
    )]
    listed = _distribution(name, counts, total)
    if listed:
        items.append(insight(f"{readable(name)} 분포", listed,
                             _evidence(sheet, cells)))
    dated = _dates(sheet, header, records)
    if dated:
        items.append(dated)
    return items, items[0].fact, total + (10 if dated else 0)


def _title(value):
    text = " ".join(str(value or "").split())
    return text if 2 <= len(text) <= 40 and not text.replace(".", "").isdigit() else ""


def _distribution(name, counts, total):
    if len(counts) < 2:
        return ""
    parts = [f"{translate(value) or value} {number(count)}건"
             for value, count in counts[:MAX_LISTED]]
    rest = len(counts) - len(parts)
    tail = f", 그 밖에 {number(rest)}개" if rest > 0 else ""
    return (f"‘{readable(name)}’ 항목은 {len(counts)}가지로 나뉩니다. "
            f"{', '.join(parts)}{tail}입니다.")


def _dates(sheet, header, records):
    found = date_column(header, records)
    if not found:
        return None
    name, ordered, counts, cells = found
    peak_value, peak_count = counts[0]
    span = (f"{period(ordered[0])}부터 {period(ordered[-1])}까지"
            if ordered[0] != ordered[-1] else period(ordered[0]))
    detail = (f" 가장 많은 날은 {period(peak_value)}로 {number(peak_count)}건입니다."
              if peak_count > 1 else "")
    return insight(
        f"{readable(name)} 분포",
        f"기록은 {span} 모두 {number(len(counts))}개 시점에 걸쳐 있습니다.{detail}",
        _evidence(sheet, cells),
    )


def _evidence(sheet, cells):
    return [reference(sheet, cell["cell"]) for cell in cells[:MAX_EVIDENCE]]
