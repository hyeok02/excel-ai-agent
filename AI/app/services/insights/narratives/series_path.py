"""Describe a complete chronologically ordered path, not only its endpoints."""


def path_direction(values):
    signs = [1 if right > left else -1 for left, right in zip(values, values[1:]) if right != left]
    changes = [sign for index, sign in enumerate(signs) if not index or sign != signs[index - 1]]
    if changes == [-1]:
        return "감소세가 이어졌습니다."
    if changes == [1]:
        return "증가세가 이어졌습니다."
    if changes == [-1, 1]:
        return "감소한 뒤 반등했습니다."
    if changes == [1, -1]:
        return "증가한 뒤 감소했습니다."
    return "증가와 감소가 반복됐습니다." if changes else "변동이 없습니다."


def series_shape(labels, values, texts):
    """One line about the whole series beyond its two endpoints.

    labels are source period labels ("2006년"), values the comparable numbers and
    texts the same values as displayed with their unit. A short series is listed
    in full. A longer one names its highest and lowest periods: evenly spaced
    sample years carry no meaning, and "rose and fell" carries no information.
    """
    if len(values) < 3:
        return ""
    direction = path_direction(values)
    shaped = "" if direction == "증가와 감소가 반복됐습니다." else direction
    if len(values) <= 4:
        listed = "기간별 기록은 " + " → ".join(f"{label} {text}" for label, text in zip(labels, texts)) + "입니다."
        return f"{listed} {shaped}".strip()
    if direction in {"감소세가 이어졌습니다.", "증가세가 이어졌습니다.", "변동이 없습니다."}:
        return direction
    high = max(range(len(values)), key=lambda index: (values[index], -index))
    low = min(range(len(values)), key=lambda index: (values[index], index))
    # An extreme at either end is already stated by the whole-period sentence.
    ends = {0, len(values) - 1}
    parts = [f"가장 {word} 시점은 {labels[index]} {texts[index]}"
             for word, index in (("높았던", high), ("낮았던", low)) if index not in ends]
    extremes = ", ".join(parts) + "입니다." if parts else ""
    # Both extremes at the ends of a back-and-forth path leave nothing new to say.
    return f"{shaped} {extremes}".strip()
