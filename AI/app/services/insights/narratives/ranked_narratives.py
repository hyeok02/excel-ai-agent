"""Source-only summaries for ranked and aggregate tables."""

from app.services.insights.narratives.narrative_values import finite, insight, number, reference
from app.services.insights.narratives.ranked_aggregates import aggregate_candidates, quantity_label
from app.services.insights.narratives.ranked_regions import ranked_regions
from app.services.insights.facts.sheet_scope import narrative_sheet_groups
from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.table_schema import column, detect_schema, share_value


def ranked_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    candidates = _sheet_candidates(primary) or _sheet_candidates(comparisons)
    selected = _select(candidates)
    if not selected:
        return [], ""
    return [item[2] for item in selected], " ".join(item[2].fact for item in selected[:2])


def _sheet_candidates(sheets):
    candidates = []
    for source_order, sheet in sheets:
        facts = sheet.get("business_facts", {})
        for region in ranked_regions(narrative_regions(facts)):
            candidates.extend(
                (*item, source_order)
                for item in _candidates(str(sheet["name"]), region)
            )
    return candidates


def _candidates(sheet, region):
    rows = region.get("rows", [])
    detected = detect_schema(rows)
    if not detected:
        return []
    header_index, schema, headers = detected
    records = [{column(cell): cell for cell in row} for row in rows[header_index + 1:]]
    results = []
    if "rank" in schema and "name" in schema:
        ranked = [_rank_candidate(sheet, region, row, schema, headers) for row in records]
        results.extend(item for item in ranked if item)
        if "category" in schema:
            results.extend(aggregate_candidates(
                sheet, records, schema, headers, include_component=False,
            ))
    else:
        results.extend(aggregate_candidates(sheet, records, schema, headers))
    return results


def _rank_candidate(sheet, region, row, schema, headers):
    rank, name = _get(row, schema, "rank"), _get(row, schema, "name")
    share, quantity = _get(row, schema, "share"), _get(row, schema, "quantity")
    if not rank or not name or not finite(rank.get("value")) or rank["value"] != 1:
        return None
    if not share or not finite(share.get("value")):
        return None
    parts, cited = [], [rank, name]
    if quantity and finite(quantity.get("value")):
        parts.append(f"{quantity_label(headers)}는 {number(quantity['value'])}")
        cited.append(quantity)
    percent = share_value(share)
    parts.append(f"비중은 {number(percent)}%")
    cited.append(share)
    title, title_cell = _title(region, headers)
    if title_cell:
        cited.append(title_cell)
    prefix = f"{title}에서 " if title else ""
    fact = f"{prefix}1위는 {name['value']}이며, {', '.join(parts)}입니다."
    return "rank", float(percent), insight(
        f"{name['value']} 1위", fact, _refs(sheet, cited), "metric"
    )


def _select(candidates):
    groups = {
        "aggregate": [item for item in candidates if item[0] in {"total", "aggregate"}],
        "rank": [item for item in candidates if item[0] == "rank"],
        "component": [item for item in candidates if item[0] == "component"],
    }
    chosen = []
    for group in ("aggregate", "rank", "component", "aggregate", "rank"):
        options = [item for item in groups[group] if item not in chosen]
        if options:
            chosen.append(max(options, key=_priority))
    remaining = sorted((item for item in candidates if item not in chosen),
                       key=_priority, reverse=True)
    return (chosen + remaining)[:5]


def _priority(candidate):
    return -candidate[3], candidate[1]


def _get(row, schema, role):
    return row.get(schema[role]) if role in schema else None


def _title(region, headers):
    title = region.get("title")
    title_cell = region.get("title_cell")
    header_values = {" ".join(str(value).split()).casefold() for value in headers.values()}
    normalized = " ".join(str(title).split()).casefold()
    if (not title or str(title).isdigit() or not isinstance(title_cell, dict)
            or normalized in header_values):
        return "", None
    return str(title).strip(), title_cell


def _refs(sheet, cells):
    return [reference(sheet, cell["cell"]) for cell in cells]
