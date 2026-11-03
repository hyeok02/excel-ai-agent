"""Source-grounded category examples and transaction-date coverage."""
import re

from app.services.insights.display.record_labels import header_words
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.narratives.narrative_values import reference


def _examples(sheet, headers, records, kind):
    # Values are quoted verbatim: a Sales category must never become revenue.
    candidates = []
    for p, header in headers.items():
        word = header_words(header["value"])
        if word not in {"category", "product", "item", "분류", "제품", "상품", "품목"}:
            continue
        values = [row.get(p, {}).get("value") for row in records]
        if not all(isinstance(v, str) and v.strip() and len(v) <= 50 for v in values):
            continue
        unique = list(dict.fromkeys(values))
        candidates.append((word not in {"category", "분류"}, p, header, unique))
    if not candidates:
        return "", []
    _, p, header, values = min(candidates, key=lambda c: c[:2])
    labels = ", ".join(f"‘{v}’" for v in values[:3])
    labels += " 등" if len(values) > 3 else ""
    noun = "분류 항목" if header_words(header["value"]) in {"category", "분류"} else "품목"
    return (f"{noun}에는 {labels}{'이 있습니다' if len(values) > 3 else ' 항목이 있습니다'}.",
            [reference(sheet, header["cell"]),
             reference(sheet, f"{records[0][p]['cell']}:{records[-1][p]['cell']}")])


def _period(sheet, headers, records, kind):
    allowed = {"date", "transaction date", "날짜", "거래일"}
    allowed |= ({"sales date", "order date", "판매일", "주문일"} if kind == "판매 내역"
                else {"purchase date", "구매일"})
    candidates = [(p, c) for p, c in headers.items() if header_words(c["value"]) in allowed]
    if len(candidates) != 1:
        return "", []
    p, header = candidates[0]
    cells = [row.get(p, {}) for row in records]
    if not all(re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ].+)?", str(c.get("value", ""))) for c in cells):
        return "", []
    dates = [date_value(c.get("value")) for c in cells]
    if not all(dates):
        return "", []
    # Source-local calendar days, with no assumption about timezone conversion.
    days = [d.date() for d in dates]
    first, last = min(days), max(days)
    def label(d):
        return f"{d.year}년 {d.month}월 {d.day}일"
    span = label(first) if first == last else f"{label(first)}부터 {label(last)}까지"
    return span, [reference(sheet, header["cell"]),
                  reference(sheet, f"{cells[0]['cell']}:{cells[-1]['cell']}")]
