"""Conservative exact-header aggregates when a model planner is unavailable.

This is not a synonym/intent guesser. Every metric, group and predicate must
bind to a source header, all remaining words must be output grammar, and the
ordinary independent request/source/calculation validator must accept the plan.
"""
import re

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.boolean_filter_language import boolean_question
from app.agent.query.boolean_filter_lexing import leaf_at
from app.agent.query.metric_request_coverage import _remove_source_phrase
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_request_literals import source_headers
from app.agent.query.tabular_request_operations import STATISTICS
from app.agent.query.tabular_request_numeric import _OPS, _PREFIX, _SUFFIX
from app.agent.query.search_terms import KOREAN_SUFFIXES

_GRAMMAR = set((
    "이 해당 파일 시트 표 원본 전체 모두 총 데이터 자료 행 기록 항목 값 조건 중 중에서 "
    "의 이 가 은 는 을 를 에 에서 인 와 과 및 그리고 별 별로 각각 기준으로 "
    "the a an file sheet table all total data rows records values value of in on from "
    "where with and by per each what is are please me show tell give calculate compare"
).split())
_ENDINGS = re.compile(r"(?:얼마|무엇|뭐)(?:입니까|인가요|인지|인가|이야|야|이죠|이지|일까요|일까)?$")
_REQUEST = re.compile(r"^(?:알려|보여|말해|계산해|구해|비교해)(?:줘|주세요|주라|줘요|줄래|주세요요)?$")


def source_aggregate_answer(question, summary, index):
    if boolean_question(question):
        return None  # The dedicated boolean path owns OR/NOT and parentheses.
    tables = build_query_tables(summary)
    named = mentioned_sources((table.sheet_name for table in tables), question)
    answers = []
    for table in tables:
        if named and table.sheet_name not in named:
            continue
        plan = source_aggregate_plan(question, table)
        if plan is None:
            continue
        answer = execute_tabular_query(plan, summary, index, question)
        if answer is not None:
            answers.append(answer)
    return answers[0] if len(answers) == 1 else None


def source_aggregate_plan(question, table):
    from app.agent.query.tabular_total_scope import total_lookup_plan
    if total := total_lookup_plan(question, table):
        return total
    headers = _headers(question, table)
    if not headers:
        return None
    spans, filters = [], []
    for column, header in headers:
        if any(start <= header.start() < end for start, end in spans):
            continue
        # A numeric leaf can stop at the value before an attached Korean
        # comparator ("20 이상인"). Prefer the complete comparison, not an
        # equality to 20 with an unexplained suffix left behind.
        numeric = _numeric_predicate(question, header, column)
        if numeric:
            condition, end = numeric
        else:
            parsed = leaf_at(question, header.start(), table)
            if parsed is None:
                continue
            condition, end, _, _ = parsed
        filters.append(condition)
        spans.append((header.start(), end))
    if len(filters) > 8:
        return None
    remainder = _mask(question, spans)
    group_ids, group_spans = [], []
    for column, header in _headers(remainder, table):
        suffix = re.match(r"\s*별(?:로)?", remainder[header.end():])
        prefix = re.search(r"\b(?:group(?:ed)?\s+)?by\s*$", remainder[:header.start()], re.I)
        if suffix or prefix:
            group_ids.append(column)
            group_spans.append((prefix.start() if prefix else header.start(),
                                header.end() + suffix.end() if suffix else header.end()))
    remainder = _mask(remainder, group_spans)
    metrics = _headers(remainder, table)
    selected = list(dict.fromkeys(column for column, _ in metrics))
    if len(selected) != 1 or len(set(group_ids)) != len(group_ids) or len(group_ids) > 3:
        return None
    remainder = _mask(remainder, [(match.start(), match.end()) for _, match in metrics])
    statistics = {key for key, pattern in STATISTICS.items() if re.search(pattern, remainder, re.I)}
    if len(statistics) != 1:
        return None
    statistic = next(iter(statistics))
    remainder = re.sub(STATISTICS[statistic], " ", remainder, flags=re.I)
    remainder = _remove_source_phrase(remainder.casefold(), table.sheet_name)
    if not _covered(remainder):
        return None
    return TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=selected, group_by=group_ids,
                            filters=filters, statistic=statistic)


def _numeric_predicate(text, header, column):
    start = header.end()
    prefix = re.match(r"\s*(?:이|가|은|는)?\s*", text[start:])
    start += prefix.end()
    for pattern in (_SUFFIX, _PREFIX):
        match = pattern.match(text, start)
        if match is None:
            continue
        operator = _OPS[" ".join(match["op"].casefold().split())]
        raw = match["number"].replace(",", "")
        value = float(raw) if "." in raw else int(raw)
        return TabularFilter(column_id=column, operator=operator, value=value,
                             value_unit="percent" if match["unit"] else "raw"), match.end()
    return None


def _headers(text, table):
    from app.agent.query.source_measure_labels import bound_header_mentions
    matches = bound_header_mentions(text, table)
    return [(column, match) for column, match in matches
            if (match.start() == 0 or not re.match(r"[A-Za-z0-9_]", text[match.start() - 1]))
            and (match.end() == len(text) or not re.match(r"[A-Za-z0-9_]", text[match.end()]))]


def _mask(text, spans):
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + " " * (end - start) + text[end:]
    return text


def _covered(text):
    # Operators, stray quoted literals, numbers and unsupported constraints
    # cannot disappear merely because a known header was also mentioned.
    if re.search(r"[0-9=<>%+*/&|()\[\]]", text):
        return False
    for token in re.findall(r"[a-z0-9_가-힣]+", text):
        forms = {token, *(token[:-len(suffix)] for suffix in KOREAN_SUFFIXES
                           if suffix and token.endswith(suffix) and len(token) > len(suffix))}
        if not any(form in _GRAMMAR or _ENDINGS.fullmatch(form) or _REQUEST.fullmatch(form)
                   for form in forms):
            return False
    return not re.sub(r"[a-z가-힣_\s,;:.?!'\"‘’“”·-]", "", text)
