"""A complete categorical grid is required before synthesizing total values."""
from dataclasses import replace
from decimal import Decimal, localcontext
import re

from app.agent.query.grouped_trend_series import grouped_series, _identities
from app.agent.query.derived_trend_calculations import share_points
from app.agent.query.trend_request import trend_request_error
from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope

_TOTAL_ROW = re.compile(r"(?:합|총|소|누)\s*계|(?<![가-힣])계(?![가-힣])|전체|총합|"
                        r"\b(?:(?:sub|grand)[ -]*)?totals?\b|\b(?:all|overall)\b", re.I)


def category_share_points(source, target, named, index):
    if re.search(r"비중|비율|증감률|증가율|감소율|평균|주당|인당|%|\b(?:ratio|share|percentage|rate|margin|average|eps|per)\b", source.metric.header, re.I):
        raise ValueError("이미 비율·평균인 지표를 더해 전체 합계로 만들지 않았습니다. 가산 가능한 원본 수치가 필요합니다.")
    _identities(source, source.records)
    groups = grouped_series(source, index)
    if len(groups) < 2:
        raise ValueError("전체를 구성하는 서로 다른 범주가 두 개 이상 필요합니다. 한 범주를 임의로 전체로 보지 않았습니다.")
    units = [unit for _, _, group_units, _ in groups for unit in group_units]
    if not all(unit.known for unit in units) or len({unit.identity for unit in units}) != 1:
        raise ValueError("전체 범주의 단위가 같고 명확한지 확인하지 못해 분모를 합산하지 않았습니다.")
    dates = {tuple(point.period for point in candidate.observations) for _, candidate, _, _ in groups}
    if len(dates) != 1:
        raise ValueError("범주별 관측 날짜가 달라 전체 합계를 확정하지 못했습니다. 누락 범주를 0으로 바꾸지 않았습니다.")
    contexts = {(point.grain, point.scenario) for _, candidate, _, _ in groups for point in candidate.observations}
    if len(contexts) != 1:
        raise ValueError("범주별 관측 주기·실적/예상 기준이 달라 하나의 전체 합계로 계산하지 않았습니다.")
    numerator, all_series, references = None, [], []
    for _, candidate, group_units, cells in groups:
        category = candidate.observations[0].entity_cells[0].value
        if _TOTAL_ROW.search(str(category)):
            raise ValueError("범주에 합계·소계·전체 행이 섞여 있습니다. 상세 행과 중복 합산하지 않았습니다.")
        _, residual = bind_explicit_metric_scope(source.request.residual, candidate.observations)
        if residual != source.request.residual:
            residual = re.sub(r"범위(?:에서|의|내)?|\brange\b", " ", residual, flags=re.I)
        if error := trend_request_error(residual, candidate.observations, named):
            raise ValueError(error)
        if any(Decimal(str(point.value.value)) < 0 for point in candidate.observations):
            raise ValueError("음수 구성값이 있어 전체의 비중으로 계산하지 않았습니다.")
        if any(parse_number_format(point.value.number_format).percent for point in candidate.observations):
            raise ValueError("원본이 백분율 값이어서 범주 합계를 전체 수량으로 해석하지 않았습니다.")
        if category == target.value:
            numerator = (candidate, group_units)
        all_series.append(candidate)
        references.extend(cells)
    if numerator is None:
        raise ValueError("요청한 범주를 전체 범주 집합에서 확인하지 못했습니다.")
    total_points = []
    for points in zip(*(candidate.observations for candidate in all_series)):
        numbers = [Decimal(str(point.value.value)) for point in points]
        with localcontext() as context:
            context.prec = max(60, sum(len(number.as_tuple().digits) + abs(number.adjusted()) for number in numbers) + 8)
            total = sum(numbers)
        if total <= 0:
            raise ValueError("전체 합계가 0 이하인 시점이 있어 비중 추이를 계산하지 않았습니다.")
        # Virtual totals are arithmetic only: callers cite the original grid.
        total_points.append(replace(points[0], value=replace(points[0].value, value=total, formula=None)))
    denominator = replace(numerator[0], observations=tuple(total_points))
    series = (numerator, (denominator, numerator[1]))
    return share_points(numerator[0], denominator, component=True), series, tuple(dict.fromkeys(references)), len(groups)
