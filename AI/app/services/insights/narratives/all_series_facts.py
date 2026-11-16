"""Every series fact the narrators can state, not only the few a report shows as cards."""
from app.services.insights.facts.sheet_scope import narrative_sheet_groups
from app.services.insights.narratives.horizontal_trends import _candidates
from app.services.insights.narratives.vertical_latest_items import _items
from app.services.insights.narratives.vertical_latest_narratives import _basis_priority
from app.services.insights.narratives.vertical_latest_series import _series


def all_series_facts(context):
    """[(basis priority, insight)] for each metric of each section, annual totals ranked first."""
    facts = []
    for sheet in context.get("sheets", []):
        if not isinstance(sheet, dict):
            continue
        series = list(_series(sheet))
        for header, section, section_cell, records, unit_note in series:
            facts.extend((_basis_priority(section), item)
                         for item in _items(sheet, header, section, section_cell, records, unit_note, series, every=True))
    primary, comparisons = narrative_sheet_groups(context)
    facts.extend((_basis_priority(str(item.title)), item) for _, item in _candidates([*primary, *comparisons]))
    return facts
