"""감소·증가를 물었을 때 각 지표의 최고점(최저점)부터 현재까지를 본다.

검색이 가져온 행의 첫 줄을 시작점으로 삼으면, 같은 질문도 검색 결과에 따라
기간이 달라져 답이 바뀐다. 실제로 같은 파일 같은 질문이 검색어에 따라
'2022-09부터'면 Other, '2023-09부터'면 Services로 갈렸다.

사람은 "가장 많이 감소한"을 보통 최고점 대비로 읽는다. 전 구간 양끝만 보면
중간에 크게 늘었다 줄어든 항목이 '증가'로 잡혀 질문에 답하지 못한다.
"""
from app.agent.query.comparison_scope import column_from_address

Point = tuple[object, object]


def peak_adjusted_metrics(
    metrics: list[dict[str, object]], points: list[Point], direction: str | None
) -> list[dict[str, object]]:
    if direction not in {"decrease", "increase"} or len(points) < 2:
        return metrics
    pick = max if direction == "decrease" else min
    return [_adjusted(metric, points, pick) for metric in metrics]


def _adjusted(metric: dict[str, object], points: list[Point], pick) -> dict[str, object]:
    reference = metric.get("start_reference")
    if not isinstance(reference, str):
        return metric
    column = column_from_address(reference.split("!")[-1])
    series = [
        (date, value, row)
        for date, row in points
        if (value := _value(row, column)) is not None
    ]
    if len(series) < 2:
        return metric
    _, end_value, end_row = series[-1]
    start_date, start_value, start_row = pick(series[:-1], key=lambda item: item[1])
    cell = _cell(start_row, column)
    if cell is None:
        return metric
    return {
        **metric,
        "start_value": start_value,
        "end_value": end_value,
        "change": round(float(end_value) - float(start_value), 10),
        "start_reference": cell.reference,
        "end_reference": _reference(end_row, column, metric),
        "start_date": start_date.date().isoformat(),
    }


def _reference(row: object, column: str, metric: dict[str, object]) -> object:
    cell = _cell(row, column)
    return cell.reference if cell is not None else metric.get("end_reference")


def _cell(row: object, column: str):
    for cell in getattr(row, "cells", ()):
        if column_from_address(cell.address) == column:
            return cell
    return None


def _value(row: object, column: str):
    cell = _cell(row, column)
    value = getattr(cell, "value", None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value
