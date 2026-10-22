"""Select complete, aligned populations before calculating a change ranking."""
from dataclasses import dataclass
import re

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.change_ranking_long import long_ranking_series
from app.agent.query.change_ranking_request import ranking_request_remainder
from app.agent.query.change_ranking_scope_guards import (
    group_restriction_error, scenario_request_error, metric_unit_request_error,
)
from app.agent.query.change_ranking_units import reconciled_group_units
from app.agent.query.change_ranking_wide import wide_ranking_candidates
from app.agent.query.metric_observation_units import ObservationUnit
from app.agent.query.metric_observation_periods import GRAINS
from app.agent.query.metric_request_coverage import uncovered_request_tokens
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_scope import explicit_ranges, _inside
from app.agent.query.trend_date_bounds import parse_trend_date_bounds
from app.agent.query.trend_selection import prepare_trend_candidate, distinct_trend_candidates
from app.agent.query.trend_source_models import TrendCandidate
from app.agent.query.trend_sources import trend_candidates
from app.agent.query.trend_request import _cadence_matches


@dataclass(frozen=True)
class RankingSources:
    series: tuple[tuple[TrendCandidate, tuple[ObservationUnit, ...]], ...] = ()
    group_label: str = "항목"
    error: str | None = None
    limitations: tuple[str, ...] = ()


def ranking_sources(question, summary, index, request):
    label = {"department": "부서", "role": "직무"}.get(request.group, "항목")
    if not getattr(index, "rows", ()):
        return RankingSources(group_label=label)
    try:
        return _sources(question, summary, index, request, label)
    except (ValueError, TypeError, ArithmeticError) as error:
        reason = str(error)
        if re.fullmatch(r"[a-z_]+", reason):
            reason = "전체 비교 대상의 날짜·값·단위·원본 범위를 확인하지 못했습니다: " + reason
        return RankingSources(group_label=label, error=reason)


def _sources(question, summary, index, request, label):
    named = mentioned_sources((sheet.name for sheet in summary.sheets), question)
    tables = [table for table in build_query_tables(summary) if not named or table.sheet_name in named]
    ranges = explicit_ranges(question)
    # Exact coordinate restrictions are checked again against every value/date.
    if ranges:
        tables = [table for table in tables if any(sheet == table.sheet_name
                  and (_inside(reference, table.reference) or _inside(table.reference, reference))
                  for sheet, reference in ranges)]
    residual = ranking_request_remainder(question, request)
    candidates = wide_ranking_candidates(residual, summary, index, tables, request.group)
    prepared = [prepare_trend_candidate(candidate, index.rows) for candidate in candidates]
    long = long_ranking_series(residual, summary, index, tables, request.group)
    prepared.extend((candidate, units) for candidate, units, _ in long)
    if not prepared and request.group is None:
        prepared = [prepare_trend_candidate(candidate, index.rows)
                    for candidate in trend_candidates(summary, index, residual)]
    if not prepared:
        raise ValueError("질문의 부서·직무·항목을 구분하는 날짜별 원본 표를 찾지 못했습니다.")
    if any(candidate.error for candidate, _ in prepared):
        raise ValueError(next(candidate.error for candidate, _ in prepared if candidate.error))
    if ranges and any(not all(any(sheet == point.value.sheet_name
            and _inside(point.value.address, reference) and _inside(point.period_cell.address, reference)
            for sheet, reference in ranges) for point in candidate.observations) for candidate, _ in prepared):
        raise ValueError("명시한 원본 범위에 비교 대상 전체의 날짜와 값이 포함되지 않습니다.")
    by_table = {}
    for candidate, units in prepared:
        by_table.setdefault(candidate.table_id, []).append((candidate, units))
    prepared = [item for group in by_table.values() for item in reconciled_group_units(group, index)]
    prepared = distinct_trend_candidates(prepared, preserve_labels=True)
    if candidates and (error := group_restriction_error(question, prepared, request.group)):
        raise ValueError(error)
    if error := scenario_request_error(question, prepared):
        raise ValueError(error)
    _alignment(prepared)
    if error := metric_unit_request_error(question, prepared):
        raise ValueError(error)
    points = [point for candidate, _ in prepared for point in candidate.observations]
    if request.basis == "adjacent":
        cadence = {kind for kind, pattern in GRAINS.items() if pattern.search(question)}
        if cadence and not all(_cadence_matches(cadence, candidate.observations) for candidate, _ in prepared):
            raise ValueError("질문에서 지정한 인접 기간의 주기와 원본 관측 주기가 다릅니다. 다른 주기의 값으로 대신하지 않았습니다.")
    for text in ([entry[2] for entry in long] if long else [residual]):
        _, text = bind_explicit_metric_scope(text, points)
        bounds, error = parse_trend_date_bounds(text, points, named)
        if error:
            raise ValueError(error)
        text = re.sub(r"범위(?:에서|의|내)?|\brange\b", " ", bounds.remainder, flags=re.I)
        if uncovered_request_tokens(text, points, named):
            raise ValueError("질문의 지표·대상·조건을 원본 비교 범위와 모두 연결하지 못했습니다. 조건을 임의로 빼고 순위를 계산하지 않았습니다.")
    if len(prepared) < 2:
        raise ValueError("순위를 비교할 서로 다른 부서·직무·항목이 두 개 이상 필요합니다.")
    limitations = tuple(dict.fromkeys(f"{candidate.table_id}: 숨겨진 {candidate.hidden_rows}개 행을 제외한 비교입니다."
                        for candidate, _ in prepared if candidate.hidden_rows))
    return RankingSources(tuple(prepared), label, limitations=limitations)


def _alignment(series):
    if len({tuple(point.period for point in candidate.observations) for candidate, _ in series}) != 1:
        raise ValueError("항목마다 관측 날짜가 달라 같은 전체 기간의 순위로 비교하지 않았습니다.")
    if len({(point.grain, point.scenario) for candidate, _ in series for point in candidate.observations}) != 1:
        raise ValueError("항목의 관측 주기 또는 실적·예상 구분이 서로 달라 순위로 비교하지 않았습니다.")
    if len({unit.identity for _, units in series for unit in units}) != 1:
        raise ValueError("항목별 단위가 달라 임의 변환하거나 순위를 매기지 않았습니다.")
    labels = [str(candidate.observations[0].label.value).casefold().strip() for candidate, _ in series]
    if len(set(labels)) != len(labels):
        raise ValueError("같은 항목의 서로 다른 원본 값이 있어 전체 비교 대상을 확정하지 못했습니다.")
    entities = [{str(cell.value) for point in candidate.observations for cell in point.entity_cells}
                for candidate, _ in series]
    if any(entity != entities[0] for entity in entities[1:]):
        raise ValueError("서로 다른 회사·지역·시나리오의 값을 같은 비교 대상으로 합치지 않았습니다.")
    if len({candidate.table_id for candidate, _ in series}) > 1 and not all(entities):
        raise ValueError("여러 표의 항목이 같은 비교 대상인지 원본 문맥으로 확인하지 못했습니다.")
