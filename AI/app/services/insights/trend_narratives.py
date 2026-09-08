"""Group related source changes; never promote a percentage over the overall metric."""
from app.services.insights.fact_trends import date_value
from app.services.insights.narrative_values import (
    finite, identity, insight, metric_name, metric_unit, number, overall, period,
)
from app.services.insights.sheet_scope import narrative_sheet_groups


def trend_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    candidates = _trend_candidates(primary) or _trend_candidates(comparisons)
    if not candidates:
        return [], ""
    first_order = min(item[0] for item in candidates)
    _, _, sheet, changes = max(
        (item for item in candidates if item[0] == first_order),
        key=lambda item: item[1],
    )
    changes.sort(key=lambda c: (not overall(c["metric"]), -abs(c["change"])))
    primary = changes[0]
    records = sheet.get("business_facts", {}).get("time_series") or sheet.get(
        "business_facts", {}).get("selected_records", [])
    subject, owner_refs = identity(sheet)
    unit = metric_unit(primary["metric"], records)
    metric = metric_name(primary["metric"])
    owner = f"{subject}의 " if subject else ""
    principal = f"{owner}{metric}는 {_change(primary, unit)}."
    timeline, timeline_refs = _timeline(primary, records, unit)
    items = [insight(f"{owner}{metric_name(primary['metric'])} 변화", principal + timeline,
                     [*owner_refs, *primary["evidence"], *timeline_refs], "trend")]
    related = [c for c in changes[1:] if c["evidence"] == primary["evidence"]
               and c["earliest_period"] == primary["earliest_period"]
               and c["latest_period"] == primary["latest_period"]][:4]
    detail = ""
    if related:
        fragments = [f"{c['metric']} 항목은 {_change(c, metric_unit(c['metric'], records) or unit, False)}"
                     for c in related]
        detail = f"같은 기간 {'. '.join(fragments)}."
        items.append(insight("주요 항목별 변화", detail,
                             [r for c in related for r in c["evidence"]], "trend"))
    return items, " ".join(
        part for part in (principal, detail, timeline.strip()) if part
    )


def _trend_candidates(sheets):
    candidates = []
    for source_order, sheet in sheets:
        facts = sheet.get("business_facts", {})
        changes = [c for c in facts.get("numeric_changes", []) if complete_change(c)]
        if changes:
            candidates.append((source_order, any(overall(c["metric"]) for c in changes),
                               sheet, changes))
    return candidates


def complete_change(change):
    if not all(change.get(k) for k in ("metric", "earliest_period", "latest_period", "evidence")):
        return False
    if not all(finite(change.get(k)) for k in (
        "earliest_value", "latest_value", "change", "change_rate_percent",
    )):
        return False
    old, new = change["earliest_value"], change["latest_value"]
    return (old != 0 and abs(new - old - change["change"]) < 0.00001
            and abs(round((new - old) / abs(old) * 100, 2) - change["change_rate_percent"]) < 0.011
            and isinstance(change["evidence"], list)
            and all(isinstance(r, str) and "!" in r for r in change["evidence"]))


def _change(change, unit, dated=True):
    old, new, delta = (number(change[k]) for k in ("earliest_value", "latest_value", "change"))
    direction = "감소했습니다" if change["change"] < 0 else "증가했습니다"
    before = f"{period(change['earliest_period'])} " if dated else ""
    after = f"{period(change['latest_period'])} " if dated else ""
    return (f"{before}{old}{unit}에서 {after}{new}{unit}{'으로' if unit else '로'} "
            f"{delta.lstrip('-')}{unit}({abs(change['change_rate_percent']):g}%) {direction}")


def _timeline(change, records, unit):
    points = {}
    evidence = set(change.get("evidence", []))
    scopes = {record.get("_trend_scope") for record in records
              if record.get("location") in evidence}
    for record in records:
        if scopes and record.get("_trend_scope") not in scopes:
            continue
        cells = record.get("values", [])
        if not cells or not record.get("location"):
            continue
        date = date_value(cells[0].get("value"))
        if date is None or not str(change["earliest_period"]) <= str(cells[0]["value"]) <= str(change["latest_period"]):
            continue
        for cell in cells[1:]:
            if cell.get("label") == change["metric"] and finite(cell.get("value")):
                points[date] = (cells[0]["value"], cell["value"], record["location"])
    ordered = [points[date] for date in sorted(points)]
    if len(ordered) < 3:
        return "", []
    # Keep both endpoints and two evenly spaced intermediate observations.
    indexes = sorted({0, len(ordered) // 3, 2 * len(ordered) // 3, len(ordered) - 1})
    selected = [ordered[index] for index in indexes]
    text = " → ".join(f"{period(date)} {number(value)}{unit}" for date, value, _ in selected)
    falling = all(a[1] > b[1] for a, b in zip(ordered, ordered[1:]))
    trend = " 이 구간에서는 감소세가 이어졌습니다." if falling else ""
    return f" 기간별 기록은 {text}입니다.{trend}", [ref for _, _, ref in ordered]
