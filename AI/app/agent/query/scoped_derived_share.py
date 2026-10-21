"""Compute category shares inside an explicitly filtered original population."""
from dataclasses import replace

from app.agent.query.derived_trend_render import render_derived
from app.agent.query.derived_trend_request import DerivedRequest
from app.agent.query.grouped_share_trend_calculations import category_share_points
from app.agent.query.grouped_share_trend_request import whole_relation, remove_whole
from app.agent.query.grouped_trend_series import grouped_series
from app.agent.query.grouped_trend_scope import filter_records
from app.agent.query.scoped_derived_sources import complete_records, dated_population
from app.agent.query.scoped_derived_render import composite_answer
from app.agent.query.tabular_query_models import TabularFilter


def scoped_share(question, source, named, index, summary=None):
    request = source.request
    if request.statistic not in {None, "sum"}:
        raise ValueError("평균·최솟값·최댓값을 범주별로 계산해 전체 합계로 더하지 않았습니다. "
                         "원본 합계의 비중인지 시점별 비중의 평균인지 계산 순서를 지정해 주세요.")
    if len(request.groups) > 1:
        raise ValueError("비중의 전체를 나눌 범주 열을 하나로 지정해 주세요. 여러 그룹의 분모를 임의로 정하지 않았습니다.")
    target = None
    if not request.groups:
        targets = []
        for condition in request.filters:
            if condition.operator != "equals" or not isinstance(condition.value, str):
                continue
            try:
                whole_relation(question, source, condition)
                targets.append(condition)
            except ValueError:
                pass
        if len(targets) != 1:
            raise ValueError("조건 범위 안에서 전체 수치 중 어느 범주의 비중인지 명확히 지정해 주세요.")
        target = targets[0]
        groups = (target.column_id,)
        filters = tuple(item for item in request.filters if item != target)
    else:
        groups, filters = request.groups, request.filters
    if any(item.column_id in groups for item in filters):
        raise ValueError("같은 범주 열에 그룹과 조건이 함께 있어 전체 분모를 확정하지 못했습니다.")
    residual = remove_whole(request.residual, source.table)
    derived_request = replace(request, groups=groups, filters=filters, residual=residual)
    population = replace(source, request=derived_request)
    records, points, bounds = dated_population(population, complete_records(source, summary, index), named)
    records = [row for row, point in zip(records, points)
               if (bounds.start is None or point.period >= bounds.start)
               and (bounds.end is None or point.period <= bounds.end)]
    records = filter_records(records, filters, source.table)
    if not records:
        raise ValueError("비중을 계산할 조건·기간 안의 원본 모집단이 없습니다.")
    population = replace(population, records=tuple(records), note=bounds.note)
    series = grouped_series(population, index)
    categories = tuple(dict.fromkeys(row[groups[0]].value for row in records))
    if len(categories) != len(series):
        raise ValueError("같은 표시 값에 서로 다른 자료형·단위의 범주가 있어 비중 대상을 확정하지 못했습니다.")
    targets = [target] if target else [TabularFilter(column_id=groups[0], operator="equals", value=value)
                                    for value in categories]
    parts = []
    for item in targets:
        values, operands, _, count = category_share_points(population, item, named, index)
        label = f"{item.value} {source.metric.header}"
        total = f"선택한 조건 범위의 전체 {source.metric.header}({source.headers[groups[0]].value}별 합계)"
        text, _ = render_derived(DerivedRequest("share", (label, total), component=True),
                                 values, (), operands, bounds.note)
        parts.append(text)
    parts.append(f"분모는 명시한 모집단 조건을 적용한 뒤 같은 시점의 {count}개 범주를 모두 합산한 값입니다. "
                 "선택 범주의 조건은 분자에만 적용하며, 누락 범주를 0으로 보거나 합계행을 중복 합산하지 않았습니다.")
    return composite_answer(question, source, parts, series,
                            ["complete_category_grid", "no_subtotal_double_count", "scoped_population_denominator"])
