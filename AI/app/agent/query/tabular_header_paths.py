"""Keep repeated child headers bound to their coordinate-defined parent field.

Nearby prose is context, not a header. Only contiguous source header bands
whose merged spans actually contain the column establish these ancestors.
No filename, sheet name, business metric or address is part of the policy.
"""
import re

from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries

from app.agent.query.ambiguity_labels import mentioned_sources, normalize_label, source_mentioned
from app.agent.query.metric_observation_cells import metric_label_matches
from app.agent.query.tabular_catalog_sources import cell_value

_TOTAL = re.compile(r"(?:계|합계|총계|총합|전체|total|grand\s+total|all)", re.I)


def column_header_path(sheet, column, cells, merged, reference):
    row, number = coordinate_to_tuple(column.header_reference.rsplit("!", 1)[1])
    table_left, _, table_right, _ = range_boundaries(reference)
    bounds = [range_boundaries(span) for span in dict.fromkeys(merged)]
    path = []
    previous = row - 1
    while previous >= max(1, row - 8):
        parents = [(left, top, right, bottom) for left, top, right, bottom in bounds
                   if left <= number <= right and left < right and bottom == previous
                   and table_left <= left <= right <= table_right
                   and (left, right) != (table_left, table_right)]
        if len(parents) != 1:
            break
        left, top, right, _ = parents[0]
        anchor = f"{get_column_letter(left)}{top}"
        text = cell_value(cells.get(anchor, {}))
        if not isinstance(text, str) or not text.strip():
            break
        path.append((f"{sheet}!{anchor}", text.strip()))
        previous = top - 1
    return tuple(reversed(path))


def header_paths_match_request(question, plan, table, tables):
    """Reject a valid value selected under a different requested parent header.

Matching an identical leaf such as Total/Public is insufficient. A referenced
parent must bind the returned measure, not merely appear elsewhere in the
table. Explicit child qualifiers further narrow that parent to the right leaf.
"""
    if not any(column.header_path for candidate in tables for column in candidate.columns):
        return True
    parent_vocabulary = {text for candidate in tables for column in candidate.columns for _, text in column.header_path}
    parents = mentioned_sources(parent_vocabulary, question)
    # Preserve the existing complete-metric aliases, but apply them to the
    # coordinate-bound parent rather than transferring them to every Total.
    parents.update(text for text in parent_vocabulary if metric_label_matches(text, question))
    for candidate in tables:
        for column in candidate.columns:
            parents.update(text for _, text in column.header_path
                           if _compound_mentioned(text, column.header, question))
    if not parents:
        return True
    selected = {column.id for column in table.columns if column.id in plan.column_ids
                and column.id not in plan.group_by}
    involved = selected | {item.column_id for item in plan.filters} | set(plan.group_by)
    if plan.order_by:
        involved.add(plan.order_by)
    matched_targets = set()
    for parent in parents:
        family = [column for column in table.columns
                  if any(normalize_label(text) == normalize_label(parent) for _, text in column.header_path)]
        if not family:
            return False
        # A named ancestor can be the broader of two nested header bands.
        # The separately named narrower ancestor supplies the actual scope.
        if any(other != parent and any(other in [text for _, text in column.header_path]
                                      for column in family) for other in parents):
            narrower = [column for column in family
                        if any(other != parent and other in [text for _, text in column.header_path]
                               for other in parents)]
            if narrower:
                family = narrower
        children = mentioned_sources((column.header for column in family), question)
        children.update(column.header for column in family if _compound_mentioned(parent, column.header, question))
        allowed = {column.id for column in family
                   if not children or column.header in children}
        if not children and plan.operation in {"lookup", "numeric_summary"} and len(selected) == 1:
            totals = {column.id for column in family if _TOTAL.fullmatch(column.header.strip())}
            if len(totals) == 1:
                allowed = totals
        if not allowed & involved:
            return False
        matched_targets.update(allowed)
    # Fields explicitly named independently (including ordinary record labels)
    # may be returned alongside the requested parent metric. An unmentioned
    # sibling under a different parent cannot piggyback on a valid filter.
    for column in table.columns:
        if column.id in selected and column.header_path and column.id not in matched_targets:
            if not source_mentioned(column.display_header, question):
                return False
    return True


def _compound_mentioned(parent, child, question):
    # Korean category+measure compounds may omit a space. Only combine actual
    # source labels, and retain full phrase boundaries (not arbitrary substrings).
    if not re.search(r"[가-힣]", parent) or len(child.strip()) < 2:
        return False
    return source_mentioned(child + parent, question) or source_mentioned(parent + child, question)
