"""A plan beside its actual on each item: 계획 · 실적, 예산 · 실적, 목표 · 실적, 기준값 · 측정값.

A plan, budget or target adds up over the items, so the actual total is read against it; a limit or
standard belongs to its own item, so each item's actual is read against its own limit.
"""
import re

from app.services.insights.narratives.layout_tables import (
    NONADDITIVE, amount, heading, label, noted, numbers, span, texts,
)
from app.services.insights.narratives.narrative_values import (
    direction_particle, finite, insight, subject_particle, topic_particle,
)

_PLAN = re.compile(r"계획|예산|목표|\b(?:plan(?:ned)?|budget(?:ed)?|target|forecast)\b", re.I)
_LIMIT = re.compile(r"기준|한도|상한|규격|\b(?:limit|standard|threshold|spec)\b", re.I)
_ACTUAL = re.compile(r"실적|실제|측정|결과|집행|\b(?:actual|result|measured)\b", re.I)


def pair_items(table, key, rows, measures):
    groups = {}
    for p in measures:
        leaf = label(table, p)
        kind = ("rate" if NONADDITIVE.search(leaf) and not _LIMIT.search(leaf) else "actual" if _ACTUAL.search(leaf)
                else "limit" if _LIMIT.search(leaf) else "plan" if _PLAN.search(leaf) else None)
        if kind and kind != "rate":
            groups.setdefault(_top(table, p), {}).setdefault(kind, p)
    names = [_named(table, key, row) for row in rows]
    items = []
    for top, kinds in groups.items():
        actual, base = kinds.get("actual"), kinds.get("plan") or kinds.get("limit")
        if actual is None or base is None:
            continue
        done, aimed = numbers(rows, actual), numbers(rows, base)
        did, aim, kind = label(table, actual), label(table, base), label(table, key)
        prefix = f"{top} " if top else ""
        if base == kinds.get("plan"):
            whole = [table["total"].get(p, {}).get("value") if table.get("total") else None for p in (actual, base)]
            done_all, aimed_all = (whole if all(finite(v) for v in whole) else (sum(done), sum(aimed)))
            shown = amount(done_all)
            fact = (f"{prefix}{did} 합계는 {aim} {amount(aimed_all)} 대비 {shown}{direction_particle(shown)} "
                    f"{aim}의 {done_all / aimed_all * 100:.1f}%입니다." if aimed_all else "")
            over = [n for n, a, b in zip(names, done, aimed) if a > b]
            under = [n for n, a, b in zip(names, done, aimed) if a < b]
            parts = [f"{aim}보다 높은 {kind}{topic_particle(kind)} {', '.join(over)}" if over else "",
                     f"낮은 {kind}{topic_particle(kind)} {', '.join(under)}" if under else ""]
            if any(parts):
                fact += " " + ", ".join(part for part in parts if part) + "입니다."
        else:
            ratios = sorted(((a / b, n, a, b) for n, a, b in zip(names, done, aimed) if b), reverse=True)
            if not ratios:
                continue
            over = [n for ratio, n, _, _ in ratios if ratio > 1]
            fact = (f"{did}{subject_particle(did)} {aim}{_object(aim)} 넘은 {kind}{topic_particle(kind)} "
                    + (f"{', '.join(over)}입니다." if over else "없습니다."))
            ratio, name, a, b = ratios[0]
            fact += (f" {aim} 대비 가장 높은 {kind}{topic_particle(kind)} {name}로, {did} {amount(a)}, {aim} {amount(b)}"
                     f"({ratio * 100:.1f}%)입니다.")
        cited = [heading(table, actual), heading(table, base), span(table, rows, actual), span(table, rows, base),
                 span(table, rows, key)]
        items.append(insight(f"{prefix}{aim} 대비 {did}", noted(fact.strip(), table["unit"]), cited, "metric",
                             topic=f"{prefix}{did}".strip()))
    return items[:3]


def _top(table, p):
    """The upper header over a column of a two-row header ('매출' over 계획 · 실적), filled from the left."""
    if len(table["header"]) < 2:
        return ""
    top = table["header"][0]
    found = [top[q] for q in sorted(top) if q <= p and str(top[q].get("value") or "").strip()]
    return " ".join(str(found[-1]["value"]).split()) if found else ""


def _named(table, key, row):
    """An item's name, with the text beside it when there is one: EX-104(스크류 회전수)."""
    name = row[key]["value"].strip()
    beside = row.get(key + 1, {}).get("value")
    return f"{name}({beside.strip()})" if isinstance(beside, str) and beside.strip() and texts([row], key + 1) else name


def _object(word):
    return "을" if subject_particle(word) == "이" else "를"
