"""Narratives for normalized, source-addressable horizontal metric series."""
from app.services.insights.display.derived_metrics import derived_metric
from app.services.insights.display.display_quality import business_priority, metric_family
from datetime import date
from app.services.insights.display.amount_units import amount_unit
from app.services.insights.narratives.narrative_values import workbook_identity
from app.services.insights.narratives.horizontal_insight import horizontal_insight as _insight
from app.services.insights.facts.sheet_scope import narrative_sheet_groups


def horizontal_trend_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    owner = workbook_identity(context)
    candidates = _candidates(primary, owner) or _candidates(comparisons, owner)
    selected, seen, families = [], set(), set()
    for _, insight in sorted(candidates, key=lambda item: item[0], reverse=True):
        metric = insight.title.rsplit(" 변화", 1)[0].casefold()
        family = metric_family(metric)
        if metric in seen or family and family in families:
            continue
        seen.add(metric)
        if family:
            families.add(family)
        selected.append(insight)
        if len(selected) == 5:
            break
    return selected, " ".join(item.fact for item in selected[:2])


def _candidates(sheets, owner=("", ())):
    results = []
    for source_order, sheet in sheets:
        facts = sheet.get("business_facts", {})
        extracted = facts.get("horizontal_series", [])
        derived = {_signature(item) for item in extracted if _derived(item)}
        unit = amount_unit(sheet)
        for series_order, series in enumerate(extracted):
            insight = _insight(str(sheet.get("name", "")), series, owner, unit)
            if insight:
                priority = (
                    not _derived(series) and _signature(series) not in derived,
                    business_priority(series.get("metric")),
                    _settled(series),
                    _basis_priority(series.get("basis")),
                    str(series.get("points", [{}])[-1].get("period", "")),
                    -source_order,
                    -series_order,
                )
                results.append((priority, insight))
    return results


def _settled(series):
    """A series running past today is a forecast, not a record of what happened."""
    return 0 if series.get("points") and str(series["points"][-1].get("period", ""))[:10] > date.today().isoformat() else 1


def _signature(series):
    """Same row, same numbers: one copy may have lost its percent formatting."""
    points = series.get("points", [])
    return (str(series.get("metric", "")).casefold(),
            *(str(point.get("value")) for point in points[:1] + points[-1:]))


def _derived(series):
    """A growth rate or ratio answers how the change changed: never the headline."""
    if _percentage(series.get("points", [])):
        return True
    name = f"{series.get('scope') or ''} {series.get('metric') or ''}"
    return derived_metric(name)


def _percentage(points):
    return all("%" in str(point.get("number_format", "")) for point in points)


def _basis_priority(value):
    text = str(value or "").casefold()
    if any(word in text for word in ("actual", "historical", "실적")):
        return 2
    if any(word in text for word in ("estimate", "forecast", "예상", "전망")):
        return 0
    return 1
