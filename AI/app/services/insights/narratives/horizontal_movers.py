"""A long list of items over months told by its total and the items that moved it.

315 usage types over six months are not read one by one in the table's order: the total comes first, then
the item that fell most, the one that rose most, and the largest in the last month, each found among all.
"""
import re

from app.services.insights.models import WorkbookInsight
from app.services.insights.facts.series_scalars import unit as cell_unit
from app.services.insights.narratives.narrative_values import reference


def summed_report(sheet, series, total):
    """(items, overview) for a summed series and its insight ``total``: the total, then what moved it."""
    from app.services.insights.narratives.horizontal_insight import _display, _period
    total = _renamed(total)
    movers = series.get("movers") or {}
    points = series["observations"]
    first, last = _period(points[0]), _period(points[-1])
    unit = cell_unit(points[0])  # written as the total is: 224.54USD
    said = lambda cell: f"{_display(cell, cell['value'])}{unit}"  # noqa: E731
    parts, cells = [], []
    for key, word in (("down", "가장 많이 줄어든"), ("up", "가장 많이 늘어난")):
        if item := movers.get(key):
            parts.append(f"{word} 항목은 {item['name']}({said(item['first'])} → {said(item['last'])})")
            cells += [item["label_cell"], item["first"]["cell"], item["last"]["cell"]]
    fact = f"{first} 대비 {last}에 " + ", ".join(parts) + "입니다." if parts else ""
    if top := movers.get("top"):
        name = f"{top['name']}({said(top['last'])})"
        fact += f"{' ' if fact else ''}{last} 기준 가장 큰 항목은 {name}입니다."
        cells += [top["label_cell"], top["last"]["cell"]]
    if not fact:
        return [total], total.fact.split("\n", 1)[0]
    cells += [point["period_cell"] for point in (points[0], points[-1])]
    moved = WorkbookInsight(title="크게 움직인 항목", fact=fact, category="change", severity="info",
                            evidence=[reference(sheet, cell) for cell in dict.fromkeys(cells)], confidence=1.0)
    return [total, moved], f"· {total.fact.split(chr(10), 1)[0]}\n· {fact}"


def _renamed(insight):
    """'월별 비용 · 전체 합계' reads as '전체 월별 비용'."""
    found = re.match(r"^(.+?) · 전체 합계", insight.fact)
    if not found:
        return insight
    name = f"전체 {found[1]}"
    return insight.model_copy(update={"fact": name + insight.fact[found.end():], "title": f"{name} 변화",
                                      "topic": name})
