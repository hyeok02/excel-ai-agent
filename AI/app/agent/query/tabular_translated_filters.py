"""Answer a plan whose filter value is the source's name for a word in the question.

"쿠키 판매수량 합계는?" is planned as Category = Cookies. Every check passes except
one: "Cookies" is not written in the question, and an unchecked translation never
authorizes a filter. Here the plan is not trusted either. For each such filter a
separate, bounded call is asked which source value each remaining question word
names, choosing only among that column's actual values. Only when exactly one
word clearly names exactly the planned value is the question read as
"쿠키(Cookies) 판매수량 합계는?" and run through the ordinary checks again. The
answer states the reading and is marked as an interpreted, source-checked answer,
never as a request-checked one. Anything less leaves the original answer as it was.
"""
import asyncio
import re
from dataclasses import replace

from app.agent.query.models import QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_request_extras import _stated_subject
from app.agent.query.tabular_request_predicates import normalize
from app.agent.query.tabular_translated_names import assigned_words, contains_as_equals, metric_word, words_naming

MAX_WORDS = 8
MAX_CONDITIONS = 4
_PARTICLE = re.compile(r"(?:에서는|에서|으로|에는|이랑|하고|와|과|랑|은|는|이|가|을|를|의|에|로|도|만)$")
# Words that state the operation, period or politeness, never a record's name.
_GENERIC = re.compile(
    r"^(?:합계|총합|평균|최대|최소|최댓값|최솟값|개수|건수|수|값|얼마|얼마야|몇|알려줘|알려주세요|보여줘|보여주세요|"
    r"어떻게|돼|되나|되나요|이야|인가요|뭐야|무엇|전체|모든|모두|각|별|기준|년|월|일|지역|항목|분류|"
    r"가장|제일|많이|적게|높은|낮은|큰|작은|순위)$")


def translated_filters(plan, table, question):
    """Equality filters on text the question does not state literally, or None when any other filter is unsupported."""
    found = []
    for condition in plan.filters:
        value = condition.value
        if condition.operator != "equals" or not isinstance(value, str) or _stated_subject(question, value):
            continue
        values = {row.values.get(condition.column_id) for row in table.rows}
        if not any(isinstance(item, str) and normalize(item) == normalize(value) for item in values):
            return None  # a value the source does not hold is not a translation of anything
        found.append(condition)
    return found


def candidate_words(question, table):
    """Words and runs of up to three adjacent words ("현재 천식 유병률") that may name a record."""
    headers = {normalize(column.header) for column in table.columns}
    tokens = re.findall(r"[가-힣]+|[A-Za-z][A-Za-z0-9&'.-]*|\S+", question)
    usable = []
    for token in tokens:
        base = _PARTICLE.sub("", token) if re.fullmatch(r"[가-힣]+", token) else token
        ok = (len(base) >= 2 and re.fullmatch(r"[가-힣]+|[A-Za-z][A-Za-z0-9&'.-]*", base) is not None
              and not _GENERIC.match(base) and normalize(base) not in headers)
        usable.append((token, base, ok))
    words = [base for _, base, ok in usable if ok]
    for size in (2, 3):
        for start in range(len(usable) - size + 1):
            run = usable[start:start + size]
            # Particles end a phrase: only its last word may carry one.
            if all(ok for _, _, ok in run) and all(token == base for token, base, _ in run[:-1]):
                words.append(" ".join(base for _, base, _ in run))
    return list(dict.fromkeys(words))[:MAX_WORDS]


async def translated_filter_answer(question, summary, data_index, intent, resolver=None, allow=True):
    plan = intent.tabular_query
    # "쿠키랑 크래커" is an OR of two planned values; each is still checked word by word.
    if not allow or plan is None:
        return None
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    bound = bind_tabular_plan(plan, tables[0]) if len(tables) == 1 else None
    if bound is None:
        return None
    table = tables[0]
    plan = bound = contains_as_equals(bound, table)
    intent = replace(intent, tabular_query=plan)
    conditions = translated_filters(bound, table, question)
    words = candidate_words(question, table)
    if not conditions or len(conditions) > MAX_CONDITIONS or not words:
        return None
    if resolver is None:
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        resolver = LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return None
    fields = {column.id: column.header for column in table.columns}
    columns = [sorted({item for row in table.rows if isinstance(item := row.values.get(condition.column_id), str)
                       and item.strip()}) for condition in conditions]
    try:
        found = await asyncio.gather(*(words_naming(resolver, words, fields[condition.column_id], values,
                                                    condition.value) for condition, values in zip(conditions, columns)))
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None
    chosen = assigned_words(found)
    if chosen is None:
        return None
    readings = [(word, condition.value, fields[condition.column_id]) for word, condition in zip(chosen, conditions)]
    rewritten = question
    for word, value, _ in readings:
        rewritten = rewritten.replace(word, f"{word}({value})", 1)
    answer = await asyncio.to_thread(execute_tabular_query, plan, summary, data_index, rewritten, intent)
    if answer is None and plan.filter_expression is not None:
        # "쿠키랑 크래커 판매수량": an OR question admits no unread word, so the metric word is read too.
        leftover = [word for word in words if not any(word in used or used in word for used in chosen)]
        try:
            metric = await metric_word(resolver, leftover, table, plan) if leftover else None
        except Exception as exception:
            raise_for_quota_exhaustion(exception)
            return None
        if metric is not None:
            readings.append((metric[0], metric[1], metric[1]))
            rewritten = rewritten.replace(metric[0], f"{metric[0]}({metric[1]})", 1)
            answer = await asyncio.to_thread(execute_tabular_query, plan, summary, data_index, rewritten, intent)
    if answer is None or answer.verification.level != QuestionVerificationLevel.REQUEST_CHECKED:
        return None
    reading = ", ".join(f"‘{word}’ → {value}" if normalize(field) == normalize(value)
                        else f"‘{word}’ → {' '.join(str(field).split())} = {value}" for word, value, field in readings)
    return answer.model_copy(update={
        "question": question, "resolved_question": rewritten,
        "answer": f"해석: {reading}\n{answer.answer}",
        "status": QuestionAnswerStatus.LIMITED, "confidence": min(answer.confidence, 0.8),
        "limitations": [*answer.limitations, f"질문의 표현을 원본 값으로 옮긴 해석({reading})이 의도와 맞는지 확인해 주세요."],
        "verification": QuestionAnswerVerification(
            level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=[check for check in answer.verification.checks if check != "request_alignment"]
            + ["semantic_alias_resolved"]),
    })
