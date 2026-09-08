"""State-of-now narratives for tables that list figures instead of a series.

Tearsheets, spec sheets and status boards hold one value per label and no time
axis, so a change narrative has nothing to compare. What they report is the
current level of each figure, largest first.
"""
from app.services.insights.derived_metrics import derived_metric, magnitude_weight
from app.services.insights.narrative_values import finite, insight, number, reference
from app.services.insights.sheet_scope import narrative_sheet_groups
from app.services.insights.table_dates import column as col
from app.services.insights.table_dates import date_axis
from app.services.insights.table_inputs import narrative_regions

MIN_FIGURES = 3
MAX_LISTED = 4
MAX_LABEL_LENGTH = 60


def snapshot_report(context):
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
        for region in narrative_regions(facts):
            report = _region_report(
                str(sheet.get("name", "")), region.get("rows", []), region.get("title"),
            )
            if report:
                results.append((source_order, *report))
    return results


def _region_report(sheet, rows, title):
    if any(date_axis(rows, index, row) for index, row in enumerate(rows)):
        return None
    figures = [figure for row in rows if (figure := _figure(row))]
    measured = [figure for figure in figures if not figure[2]]
    if len(measured) < MIN_FIGURES:
        return None
    measured.sort(key=lambda figure: magnitude_weight(figure[1]["value"]), reverse=True)
    scope = f"{' '.join(str(title).split())}의" if title else "이 표의"
    items = [insight(
        f"{' '.join(str(title).split())} 주요 수치" if title else "주요 수치",
        f"{scope} 주요 수치는 {_listing(measured[:MAX_LISTED])}입니다.",
        _evidence(sheet, measured[:MAX_LISTED]), "metric",
    )]
    ratios = [figure for figure in figures if figure[2]][:MAX_LISTED]
    if len(ratios) >= 2:
        items.append(insight(
            "비율 지표",
            f"함께 기록된 비율 지표는 {_listing(ratios)}입니다.",
            _evidence(sheet, ratios), "metric",
        ))
    return items, items[0].fact, len(measured)


def _figure(row):
    """A label-and-one-number row: the shape a status table repeats."""
    numeric = [cell for cell in row if finite(cell.get("value"))]
    if len(numeric) != 1:
        return None
    value = numeric[0]
    labels = [cell for cell in row
              if isinstance(cell.get("value"), str) and cell["value"].strip()
              and col(cell) < col(value)]
    if not labels:
        return None
    label = min(labels, key=col)
    name = " ".join(str(label["value"]).split())
    if len(name) > MAX_LABEL_LENGTH:
        return None
    return label, value, derived_metric(name, [value])


def _listing(figures):
    return ", ".join(
        f"{' '.join(str(label['value']).split())} {number(value['value'])}"
        for label, value, _ in figures
    )


def _evidence(sheet, figures):
    return [reference(sheet, cell["cell"])
            for label, value, _ in figures for cell in (label, value)]
