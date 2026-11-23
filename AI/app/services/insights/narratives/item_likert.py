"""Items over an answer scale (매우만족 · 만족 · 보통 · 불만 · 매우불만): each item's share of good and bad answers.

The columns are counts of one item's answers, so a row adds up to the item's answers and the scale's good
and bad ends are read from the column names, not from their order.
"""
import re

from app.services.insights.narratives.layout_tables import heading, label, numbers, span
from app.services.insights.narratives.narrative_values import insight, number, subject_particle

_GOOD = re.compile(r"만족|그렇다|좋음|좋다|긍정|찬성|\b(?:agree|satisfied|good|excellent|positive|likely)\b", re.I)
_BAD = re.compile(r"불만|않|나쁨|나쁘|부정|반대|\b(?:disagree|dissatisfied|poor|bad|negative|unlikely)\b", re.I)


def likert_items(table, key, rows, measures):
    names = {p: label(table, p) for p in measures}
    good = [p for p in measures if _GOOD.search(names[p]) and not _BAD.search(names[p])]
    bad = [p for p in measures if _BAD.search(names[p])]
    if len(measures) < 3 or not good or not bad:
        return []
    counts = {p: numbers(rows, p) for p in measures}
    if any(value < 0 or not float(value).is_integer() for values in counts.values() for value in values):
        return []
    totals = [sum(counts[p][index] for p in measures) for index in range(len(rows))]
    if not all(totals):
        return []
    items = [row[key]["value"].strip() for row in rows]
    share = lambda side, index: sum(counts[p][index] for p in side) / totals[index] * 100  # noqa: E731
    liked = {item: share(good, index) for index, item in enumerate(items)}
    disliked = {item: share(bad, index) for index, item in enumerate(items)}
    high, low, worst = max(liked, key=liked.get), min(liked, key=liked.get), max(disliked, key=disliked.get)
    good_names, bad_names = "·".join(names[p] for p in good), "·".join(names[p] for p in bad)
    cited = [*(heading(table, p) for p in measures), *(span(table, rows, p) for p in measures), span(table, rows, key)]
    answered = sum(totals)
    liked_all = sum(counts[p][index] for p in good for index in range(len(rows)))
    first = (f"긍정 응답({good_names}) 비율은 {high}{subject_particle(high)} {liked[high]:.1f}%로 가장 높고, "
             f"{low}{subject_particle(low)} {liked[low]:.1f}%로 가장 낮습니다.")
    second = (f"부정 응답({bad_names}) 비율은 {worst}{subject_particle(worst)} {disliked[worst]:.1f}%로 가장 높습니다. "
              f"전체 응답 {number(answered)}건 중 긍정 응답은 {number(liked_all)}건({liked_all / answered * 100:.1f}%)입니다.")
    kind = label(table, key)
    return [insight(f"{kind}별 긍정 응답 비율", first, cited, "metric", topic=kind),
            insight(f"{kind}별 부정 응답 비율", second, cited, "metric", topic=kind)]
