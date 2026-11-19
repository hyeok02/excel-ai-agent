"""Answer a plan whose filter value is the source's name for a word in the question.

"쿠키 판매수량 합계는?" is planned as Category = Cookies, but "Cookies" is not written in the question and an
unchecked translation never authorizes a filter. A bounded call reads which source value each question word names,
among that column's values only; when exactly one word names the planned value, the question is read as
"쿠키(Cookies) 판매수량 합계는?" and run through the ordinary checks again, stated as an interpreted reading.
"""
import asyncio
import re
from dataclasses import replace

from app.agent.query.models import QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_column_values import column_values
from app.agent.query.tabular_explicit_scope import asked_part
from app.agent.query.tabular_request_extras import _stated_subject
from app.agent.query.tabular_request_predicates import normalize
from app.agent.query.tabular_translated_rows import every_row, ranked_members, run_checked
from app.agent.query.joined_names import joined_names
from app.agent.query.tabular_translated_names import (
    affirmed_columns, assigned_words, column_words, contains_as_equals, names_no_member, words_naming)

MAX_WORDS = 8
MAX_CONDITIONS = 4
_PARTICLE = re.compile(r"(?:에서는|에서|으로|에는|이랑|하고|와|과|랑|은|는|이|가|을|를|의|에|로|도|만)$")
# Words that state the operation, period or politeness, never a record's name.
_GENERIC = re.compile(
    r"^(?:합계|총합|평균|최대|최소|최댓값|최솟값|개수|건수|수|값|얼마|얼마야|몇|알려줘|알려주세요|보여줘|보여주세요|"
    r"어떻게|돼|되나|되나요|이야|인가요|뭐야|무엇|전체|모든|모두|각|별|기준|년|월|일|지역|항목|분류|"
    r"가장|제일|많이|적게|높은|낮은|큰|작은|순위)$")


def translated_filters(plan, table, question, index=None):
    """Equality filters on text the question does not state literally, or None when any other filter is unsupported."""
    found = []
    for condition in plan.filters:
        value = condition.value
        if condition.operator != "equals" or not isinstance(value, str) or _stated_subject(question, value):
            continue
        values = set(column_values(table, condition.column_id, index))
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
    if not allow or plan is None:  # "쿠키랑 크래커" is an OR of two values, each still read word by word
        return None
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    bound = bind_tabular_plan(plan, tables[0]) if len(tables) == 1 else None
    if bound is None:
        return None
    table = tables[0]
    plan = bound = contains_as_equals(bound, table)
    intent = replace(intent, tabular_query=plan)
    conditions = translated_filters(bound, table, question, data_index)
    loose = [item for item in plan.filters if item.operator == "contains" and isinstance(item.value, str)
             and not _stated_subject(question, item.value)]
    if not conditions and loose:  # "contains Asthma" the question never says: a lookup shows every row
        return await every_row(plan, summary, data_index, question, intent, loose, [[]] * len(loose), [False] * len(loose))
    words = candidate_words(asked_part(question), table)  # a follow-up's scope names no record
    # Column names count too: "보험가액" for InsuredValue, when no value needs reading.
    unstated = [c.header for c in table.columns if c.id in plan.column_ids and not _stated_subject(question, c.header)]
    if conditions is None or len(conditions) > MAX_CONDITIONS or not words or not conditions and not unstated:
        return None
    if resolver is None:
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        resolver = LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return None
    fields = {column.id: column.header for column in table.columns}
    columns = [sorted({item for item in column_values(table, condition.column_id, data_index)
                       if isinstance(item, str) and item.strip()}) for condition in conditions]
    try:  # a yes/no column the question names is read as its "yes" ("지진" → Earthquake = Y)
        affirmed = await affirmed_columns(resolver, words, table, conditions, question)
        found = await asyncio.gather(*(words_naming(resolver, words, fields[condition.column_id], values,
                                                    condition.value) for condition, values in zip(conditions, columns)))
        found = [[affirmed[index]] if index in affirmed else named for index, named in enumerate(found)]
        totals = [named == [] and await names_no_member(resolver, words, fields[condition.column_id], values,
                                                        condition.value)
                  for condition, values, named in zip(conditions, columns, found)]
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None
    chosen = assigned_words([named for named, total in zip(found, totals) if not total])
    if chosen is None:
        return await every_row(plan, summary, data_index, question, intent, conditions, found, totals)
    picked = iter(chosen)
    readings = [(None if total else next(picked), condition.value, fields[condition.column_id])
                for condition, total in zip(conditions, totals)]
    # Words naming columns are read too: one naming a column the plan never reads rejects it,
    # and one naming the computed column is stated ("판매수량" → Qty).
    leftover = joined_names([word for word in words if not any(word in used or used in word for used in chosen if used)],
                            asked_part(question))  # "잉글랜드와 웨일스" is one name: England and Wales
    try:
        columns_named, conflict = await column_words(resolver, leftover, table, plan) if leftover else ([], False)
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None
    if conflict:
        return None
    readings += [(word, header, header) for word, header in columns_named if not _stated_subject(question, header)]
    if not readings:
        return None
    rewritten = question
    for word, value, field in readings:
        label = f"{field} {value}" if word in affirmed.values() else value  # "Y" alone fits every yes/no column
        rewritten = rewritten.replace(word, f"{word}({label})", 1) if word else f"{rewritten.rstrip()} ({value})"
    answer = await run_checked(plan, summary, data_index, rewritten, intent, question)
    if answer is None or answer.verification.level != QuestionVerificationLevel.REQUEST_CHECKED and not ranked_members(answer):
        return None
    reading = ", ".join(f"전체 행 → {' '.join(str(field).split())} = {value}" if word is None
                        else f"‘{word}’ → {value}" if normalize(field) == normalize(value)
                        else f"‘{word}’ → {' '.join(str(field).split())} = {value}" for word, value, field in readings)
    return answer.model_copy(update={
        "question": question, "resolved_question": rewritten,
        "answer": f"해석: {reading}\n{answer.answer}",
        "status": QuestionAnswerStatus.LIMITED, "confidence": min(answer.confidence, 0.8),
        "limitations": [*answer.limitations, f"질문의 표현을 원본 값으로 옮긴 해석({reading})이 의도와 맞는지 확인해 주세요."],
        "verification": QuestionAnswerVerification(
            level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=list(dict.fromkeys([check for check in answer.verification.checks if check != "request_alignment"]
                                      + ["semantic_alias_resolved"]))),
    })
