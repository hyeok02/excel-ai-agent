"""Separate explicitly named metrics from ambiguous copies of one metric."""
from app.agent.query.metric_request_coverage import _remove_source_phrase
from app.agent.query.trend_labels import trend_label_spellings

MAX_COMPARISON_SERIES = 6


def comparison_candidates(question, candidates):
    """Limit only genuine multi-metric requests, retaining all copies/errors."""
    explicit = explicit_metric_labels(question, candidates)
    if len(explicit) < 2:
        return candidates
    return [candidate for candidate in candidates if (label := _label(candidate)) is None
            or label.casefold().strip() in explicit]


def _label(candidate):
    cell = candidate.observations[0].label if candidate.observations else next(iter(candidate.context), None)
    return str(cell.value) if cell is not None else None


def explicit_metric_labels(question, candidates):
    labels = {label for candidate in candidates if (label := _label(candidate)) is not None}
    remaining, selected = question.casefold(), set()
    # "Employees" inside "Total Employees" is not a second requested metric.
    for label in sorted(labels, key=lambda value: max(map(len, trend_label_spellings(value))), reverse=True):
        reduced = remaining
        for spelling in trend_label_spellings(label):
            reduced = _remove_source_phrase(reduced, spelling)
        if reduced != remaining:
            selected.add(label.casefold().strip())
            remaining = reduced
    return selected


def comparison_missing_metrics(question, candidates, prepared_valid):
    explicit = explicit_metric_labels(question, candidates)
    valid = {_label(candidate).casefold().strip() for candidate, _ in prepared_valid}
    return sorted(explicit - valid) if len(explicit) >= 2 else []


def explicit_series(question, prepared):
    grouped = {}
    explicit = explicit_metric_labels(question, [candidate for candidate, _ in prepared])
    for candidate, units in prepared:
        label = str(candidate.observations[0].label.value)
        if label.casefold().strip() not in explicit:
            continue
        grouped.setdefault(label.casefold().strip(), []).append((candidate, units))
    if len(grouped) < 2 or any(len(items) != 1 for items in grouped.values()):
        return []
    return [items[0] for items in grouped.values()]


def comparison_limits(series):
    """No intersection join, implicit conversion or cross-entity substitution."""
    points = [candidate.observations for candidate, _ in series]
    limitations = []
    if len({tuple(point.period for point in items) for items in points}) != 1:
        limitations.append("항목마다 관측 날짜가 달라 같은 시점의 차이나 순위를 계산하지 않았습니다.")
    if len({(items[0].grain, items[0].scenario) for items in points}) != 1:
        limitations.append("항목의 관측 주기 또는 실적·예상 구분이 달라 수치를 직접 비교하지 않았습니다.")
    if not all(unit.known for _, units in series for unit in units):
        limitations.append("일부 항목의 수량·통화 단위를 확정하지 못했습니다. 각 원본 저장값의 추이만 표시합니다.")
    elif len({units[0].identity for _, units in series}) != 1:
        limitations.append("항목별 단위가 달라 값을 변환하거나 직접 차이를 계산하지 않았습니다.")
    entities = [{str(cell.value) for point in items for cell in point.entity_cells} for items in points]
    same_table = len({candidate.table_id for candidate, _ in series}) == 1
    if not same_table and (not all(entities) or any(value != entities[0] for value in entities[1:])):
        limitations.append("항목들이 같은 대상의 값인지 원본 문맥으로 확정하지 못해 직접 차이를 계산하지 않았습니다.")
    for candidate, _ in series:
        if candidate.hidden_rows:
            limitations.append(f"{candidate.table_id}: 숨겨진 {candidate.hidden_rows}개 행을 제외한 추이입니다.")
    notes = {getattr(candidate, "period_note", "") for candidate, _ in series}
    if len(notes) > 1:
        limitations.append("각 항목의 원본 기준일·비교 기간 설명이 달라 같은 기간의 차이를 계산하지 않았습니다.")
    return limitations
