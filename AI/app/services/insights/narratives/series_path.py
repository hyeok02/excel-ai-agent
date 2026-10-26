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
