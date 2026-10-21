"""Compose source-bound conditions, grouping and deterministic derived trends."""
import re

from app.agent.query.derived_trend_answers import unavailable
from app.agent.query.derived_trend_request import GROWTH, SHARE, TEMPORAL, YOY, MOM, PREVIOUS
from app.agent.query.grouped_trend_sources import grouped_sources
from app.agent.query.scoped_derived_request import clean_scoped_question, source_operation
from app.agent.query.scoped_derived_growth import scoped_growth
from app.agent.query.scoped_derived_share import scoped_share
from app.agent.query.tabular_catalog import build_query_tables


def scoped_derived_trend_answer(question, summary, index):
    temporal = TEMPORAL.search(question) or re.search(r"비교|\bcompar(?:e|ison)\b", question, re.I)
    if not (GROWTH.search(question) or SHARE.search(question)) or not temporal:
        return None
    tables = build_query_tables(summary)
    clean, operation = clean_scoped_question(question, tables, index)
    if not (GROWTH.search(operation) or SHARE.search(operation)):
        return None
    try:
        sources, named = grouped_sources(clean, summary, index)
        if not sources:
            return None
        if SHARE.search(operation) and not GROWTH.search(operation) and all(
                not source.request.groups and len(source.request.filters) <= 1 for source in sources):
            return None  # Preserve the established simple part/whole adapter.
        if len(sources) != 1:
            raise ValueError("조건·그룹 파생 추이의 원본 표 또는 수치 열이 여러 개입니다. 대상을 하나로 지정해 주세요.")
        return scoped_derived_from_source(question, sources[0], named, index, summary)
    except (ValueError, TypeError, ArithmeticError) as error:
        return unavailable(question, str(error) or "조건·그룹 파생 계산을 원본과 대조하지 못했습니다.")


def scoped_derived_from_source(question, source, named, index, summary=None):
    """Adapters may supply complete joined records with summary=None.

    request.residual must already have supported derived syntax removed while
    preserving the original date bounds and every unconsumed request token.
    """
    operation = source_operation(question, source)
    growth, share = bool(GROWTH.search(operation)), bool(SHARE.search(GROWTH.sub(" ", operation)))
    if not growth and not share:
        return None
    try:
        if growth and share:
            raise ValueError("비중의 증감률처럼 겹친 파생 계산은 각각 질문해 주세요.")
        if growth:
            return scoped_growth(question, source, named, index, summary)
        if any(pattern.search(operation) for pattern in (YOY, MOM, PREVIOUS)):
            raise ValueError("비중과 전월·전년 기준 계산을 함께 요구한 경우 계산 순서를 임의로 정하지 않았습니다.")
        return scoped_share(question, source, named, index, summary)
    except (ValueError, TypeError, ArithmeticError) as error:
        return unavailable(question, str(error) or "조건·그룹 파생 계산을 원본과 대조하지 못했습니다.")
