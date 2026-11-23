"""Items over period columns (FY2021 … FY2024, 1월 · 2월): each item's change, read like a time series."""
import re

from app.services.insights.narratives.layout_tables import TOTAL, amount, change, heading, label, noted, span
from app.services.insights.narratives.narrative_values import finite, insight

PERIOD = re.compile(r"^(?:FY\s*'?\d{2,4}[AEFPB]?|(?:19|20)\d{2}\s*(?:년|[AEFPB])?|(?:1[0-2]|[1-9])\s*월|[1-4]\s*분기|Q\s*[1-4]|[1-4]\s*Q"
                    r"|상반기|하반기|H\s*[12]|(?:19|20)\d{2}\s*[-./ ]?\s*(?:Q[1-4]|[1-4]Q|H[12]|[1-4]\s*분기|상반기|하반기))$",
                    re.I)


def period_items(table, key, rows, measures):
    periods = [p for p in measures if PERIOD.match(_period(table, p))]
    others = [p for p in measures if p not in periods and not TOTAL.search(label(table, p))]
    if len(periods) < 2 or others:
        return []
    lines = [row for row in table["rows"] if isinstance(row.get(key, {}).get("value"), str)
             and row[key]["value"].strip() and all(finite(row.get(p, {}).get("value")) for p in periods)]
    series = sorted(((" ".join(row[key]["value"].split()), row) for row in lines),  # totals and bottom lines first
                    key=lambda item: not (TOTAL.search(item[0]) or re.match(r"^net\s+income", item[0], re.I)))
    total = table.get("total")
    if total and all(finite(total.get(p, {}).get("value")) for p in periods):
        series.insert(0, (" ".join(str(total.get(key, {}).get("value") or "합계").split()), total))
    names = [_period(table, p) for p in periods]
    cited = [*(heading(table, p) for p in periods), *(span(table, rows, p) for p in periods), span(table, rows, key)]
    items = []
    for name, row in series[:4]:
        values = [float(row[p]["value"]) for p in periods]
        fact = f"{name}: {names[0]} {_said(values[0], values[-1], names[-1])}."
        if len(periods) >= 3:
            fact += f"\n최근 구간은 {names[-2]} {_said(values[-2], values[-1], names[-1])}."
        if len(periods) >= 4:
            high, low = values.index(max(values)), values.index(min(values))
            ends = {0, len(values) - 1}
            peaks = [f"가장 높았던 시점은 {names[high]} {amount(values[high])}" for _ in [1] if high not in ends]
            peaks += [f"가장 낮았던 시점은 {names[low]} {amount(values[low])}" for _ in [1] if low not in ends]
            if peaks:
                fact += "\n" + ", ".join(peaks) + "입니다."
        refs = [*cited, *(span(table, [row], p) for p in periods)]
        items.append(insight(f"{name} 변화", noted(fact, table["unit"]), refs, "change", topic=name))
    return items


def _said(before, after, last):
    return change(before, after).replace("에서 ", f"에서 {last} ", 1)


def _period(table, p):
    """The header text over a column that names a period: '2023A' above a '$' unit line."""
    texts = [" ".join(str(row[p].get("value") or "").split()) for row in table["header"] if p in row]
    return next((text for text in texts if PERIOD.match(text)), label(table, p))
