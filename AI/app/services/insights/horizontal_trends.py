"""Narratives for normalized, source-addressable horizontal metric series."""
from app.services.insights.derived_metrics import derived_metric
from app.services.insights.glossary import readable
from app.services.insights.display_quality import business_priority, metric_family
from app.services.insights.models import WorkbookInsight
from datetime import date

from app.services.insights.narrative_values import (
    PER_SHARE, amount_unit, number, period, reference, workbook_identity,
)
from app.services.insights.sheet_scope import narrative_sheet_groups


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
    points = series.get("points", [])
    last = str(points[-1].get("period", "")) if points else ""
    return 0 if last[:10] > date.today().isoformat() else 1


def _insight(sheet, series, owner=("", ()), unit=("", ())):
    points = series.get("points", [])
    if len(points) < 2:
        return None
    earliest, latest = points[0], points[-1]
    old, new = float(earliest["value"]), float(latest["value"])
    if old == new:
        return None
    metric = str(series.get("metric", "")).strip()
    scope = str(series.get("scope") or "").strip()
    holder, holder_refs = owner
    named = (f"{readable(scope)}의 {readable(metric)}" if scope
             else readable(metric))
    subject = f"{holder}의 {named}" if holder else named
    money, money_refs = unit
    if money and PER_SHARE.search(f"{scope} {metric}"):
        money, money_refs = "", []
    if _percentage(points):
        old_text, new_text = _percent(old, earliest), _percent(new, latest)
        fact = (
            f"{subject}: {period(earliest['period'])} {old_text}에서 "
            f"{period(latest['period'])} {new_text}로 {_direction(old, new)}했습니다."
        )
    else:
        change = new - old
        rate = abs(change / old * 100) if old else None
        change_text = f"{number(abs(change))}{money}"
        if rate is not None:
            change_text += f"({rate:.2f}%)"
        fact = (
            f"{subject}: {period(earliest['period'])} {number(old)}{money}에서 "
            f"{period(latest['period'])} {number(new)}{money}로 "
            f"{change_text} {_direction(old, new)}했습니다."
        )
    evidence = [
        series.get("scope_cell"), series.get("label_cell"),
        earliest.get("period_cell"), earliest.get("value_cell"),
        latest.get("period_cell"), latest.get("value_cell"),
    ]
    return WorkbookInsight(
        title=f"{subject} 변화",
        fact=fact,
        category="trend",
        severity="info",
        evidence=[*holder_refs, *money_refs,
                  *(reference(sheet, cell) for cell in dict.fromkeys(evidence) if cell)],
        confidence=1.0,
    )


def _signature(series):
    """Same row, same numbers: one copy may have lost its percent formatting."""
    points = series.get("points", [])
    ends = [points[0].get("value"), points[-1].get("value")] if points else []
    return (str(series.get("metric", "")).casefold(), *(str(value) for value in ends))


def _derived(series):
    """A growth rate or ratio answers how the change changed: never the headline."""
    if _percentage(series.get("points", [])):
        return True
    name = f"{series.get('scope') or ''} {series.get('metric') or ''}"
    return derived_metric(name)


def _percentage(points):
    return all("%" in str(point.get("number_format", "")) for point in points)


def _percent(value, point):
    number_format = str(point.get("number_format", ""))
    display = value if "\\%" in number_format else value * 100
    return f"{number(display)}%"


def _direction(old, new):
    return "감소" if new < old else "증가"


def _basis_priority(value):
    text = str(value or "").casefold()
    if any(word in text for word in ("actual", "historical", "실적")):
        return 2
    if any(word in text for word in ("estimate", "forecast", "예상", "전망")):
        return 0
    return 1
