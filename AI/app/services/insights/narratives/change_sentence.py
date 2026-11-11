"""One sentence shape for a series change, whichever way the source lays out its periods.

Years across columns (천식 유병률) and years down rows (공기질 등급별 비율) are read by
different code, but both state the change the same way: the subject, the whole
period first, then the latest step, then the path's shape.
"""
import re

from app.services.insights.narratives.narrative_values import direction_particle, joining_particle, number

_SHOWN = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _shown(text, raw):
    """(value as displayed, its decimals, scale, text after it): 5.5 for a stored 5.46, 1.2 for 1.2억."""
    found = list(_SHOWN.finditer(text))
    if not found:
        return raw, None, 1, ""
    digits, tail = found[-1].group(), text[found[-1].end():]
    shown, decimals = float(digits.replace(",", "")), len(digits.partition(".")[2])
    tolerance = 0.5 * 10 ** -decimals + 1e-9
    # 1.2억 or 12K: the display divides by a power of ten the text names after the number.
    scales = [10 ** power for power in range(0, 13, 3)] + [10 ** 4, 10 ** 8]
    scale = next((size for size in scales if abs(abs(raw) / size - shown) <= tolerance), None)
    if scale is None:
        return raw, None, 1, tail
    return (-shown if raw < 0 else shown), decimals, scale, tail


def _delta(before, after, old, new):
    """The change readers can check by subtracting the two values they see, in the scale they see."""
    left, left_places, left_scale, _ = _shown(before, old)
    right, right_places, right_scale, tail = _shown(after, new)
    if left_places is None or right_places is None or left_scale != right_scale:
        return abs(new - old), ""
    return round(abs(right - left), max(left_places, right_places)), tail if right_scale != 1 else ""


def change_sentence(before, after, old, new, unit=""):
    """'1997년 5.5%에서 2024년 3.6%로 1.9%p 감소했습니다.' for already formatted endpoints."""
    change, scaled_unit = _delta(before, after, old, new)
    if old == new or not change:
        return f"{before}{joining_particle(before)} {after}{direction_particle(after)} 시작과 마지막 값이 같습니다."
    direction = "감소" if new < old else "증가"
    if unit.strip() == "%":
        return f"{before}에서 {after}{direction_particle(after)} {number(change)}%p {direction}했습니다."
    delta = f"{number(change)}{unit or scaled_unit}"
    if old:
        delta += f"({abs((new - old) / old * 100):.2f}%)"
    return f"{before}에서 {after}{direction_particle(after)} {delta} {direction}했습니다."


def change_fact(subject, whole, recent="", shape=""):
    """'주어: 전체 기간 변화' then '최근 구간은 …' and the shape, one reading per line."""
    lines = [f"{subject}: {whole}", f"최근 구간은 {recent}" if recent else "", shape]
    return "\n".join(line for line in lines if line)
