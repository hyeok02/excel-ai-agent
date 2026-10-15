"""Separate a numeric confirmation premise from a source-verified lookup."""
import re

from app.agent.query.metric_observation_periods import SCENARIOS, requested_periods
from app.agent.query.models import (
    QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel,
)
from app.agent.query.question_date_mentions import calendar_mentions

_NUMBER = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_UNIT = (
    r"(?:[%$€£₩¥]|명|건|주|"
    r"(?:(?:백만|십억|천만|천|만|억|조)\s*)?(?:미국\s*)?(?:달러|원|유로|엔|파운드)|"
    r"(?:(?:million|billion|thousand)s?\s*)?(?:USD|EUR|KRW|JPY|GBP|dollars?|euros?)|"
    r"(?:million|billion|thousand)s?)"
)
_CONFIRM = (
    r"(?:맞(?:지|아|나요|습니까)|(?:이?라는|인)\s*(?:거지|뜻이야|뜻인가요)|"
    r"이지|인가요|인가|맞다는\s*거지|(?:is\s+that\s+)?(?:right|correct))"
)
_PREMISE = re.compile(
    rf"(?P<amount>{_NUMBER})\s*(?:{_UNIT})?\s*(?:가|이|은|는)?\s*{_CONFIRM}\s*[?!.]*$", re.I,
)
_ALTERNATIVES = {"actual": "예상", "estimate": "실적"}


def metric_premise_answer(question, summary, index, intent=None):
    """Return only independently validated values, never a yes/no certification.

    The asserted number does not select a source row or scenario. Unsupported
    qualifiers remain in the lookup, so the normal metric guards still apply.
    """
    query = _lookup_question(question)
    if query is None:
        return None
    from app.agent.query.metric_observation_answers import metric_observation_answer

    answer = metric_observation_answer(query, summary, index, intent)
    note = "질문에 제시한 수치와 전제를 그대로 확인한 답변은 아닙니다. 원본 기준 조회 결과입니다."
    if not _verified(answer):
        requests = requested_periods(query)
        if len(requests) != 1 or requests[0].scenario not in _ALTERNATIVES:
            return None
        requested = requests[0].scenario
        observations = _requested_observations(query, index)
        if (not observations
                or any(requests[0].matches(item.period, item.grain, item.scenario) for item in observations)
                or any(SCENARIOS[requested].search(str(cell.value)) for item in observations
                       for cell in (item.label, *item.entity_cells))):
            return None  # Never replace a qualifier inside a source metric/entity name.
        replacement = _ALTERNATIVES[requested]
        alternative = _alternate_question(query, requested, replacement)
        if alternative is None:
            return None
        answer = metric_observation_answer(alternative, summary, index, intent)
        if not _verified(answer):
            return None
        requested_label = "실적" if requested == "actual" else "예상"
        note = (f"질문에서 요청한 {requested_label} 값은 확인하지 못했습니다. "
                f"아래는 같은 대상·기간에 원본이 명시한 {replacement} 값입니다. "
                "질문의 전제가 맞다는 의미는 아닙니다.")
    return answer.model_copy(update={
        "question": question,
        "answer": note + "\n\n" + answer.answer,
        "status": QuestionAnswerStatus.LIMITED,
        "confidence": min(answer.confidence, 0.8),
        "limitations": [*answer.limitations, "확인형 질문의 전제와 원본에서 조회한 값을 구분했습니다."],
        "verification": QuestionAnswerVerification(
            level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=[check for check in answer.verification.checks if check != "request_alignment"]
                   + ["premise_not_confirmed"],
        ),
    })


def _verified(answer):
    return answer is not None and answer.verification.level == QuestionVerificationLevel.REQUEST_CHECKED


def _requested_observations(question, index):
    """Conflicting or uncached requested values are not permission to swap cases."""
    from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
    from app.agent.query.metric_observation_scope import _bind_entity_scope
    from app.agent.query.metric_observation_guards import _scope_references
    from app.agent.query.metric_observations import horizontal_observations

    rows = list(index.rows)
    named = {row.sheet_name for row in rows if row.sheet_name.casefold() in question.casefold()}
    if any(pattern.search(name) for name in named for pattern in SCENARIOS.values()):
        return []
    if named:
        rows = [row for row in rows if row.sheet_name in named]
    observations, scoped = bind_explicit_metric_scope(question, horizontal_observations(rows, question))
    observations = _bind_entity_scope(scoped, observations, rows, named) or []
    if _scope_references(scoped, observations, rows, named) is None:
        return []
    # A mixed-script identifier must not bind from its English fragment alone.
    for item in observations:
        for cell in item.entity_cells:
            if not (re.search(r"[가-힣]", str(cell.value)) and re.search(r"[a-z]", str(cell.value), re.I)):
                continue
            tokens = re.findall(r"[a-z0-9가-힣]+", str(cell.value).casefold())
            identity = " ".join(token for token in tokens if token not in {"inc", "llc", "ltd", "corp", "corporation"})
            if identity not in " ".join(re.findall(r"[a-z0-9가-힣]+", question.casefold())):
                return []
    return observations


def _alternate_question(question, requested, replacement):
    modifiers = list(SCENARIOS[requested].finditer(question))
    if len(modifiers) != 1:
        return None
    modifier = modifiers[0]
    start, end, *_ = calendar_mentions(question)[0]
    gap = question[end:modifier.start()] if end <= modifier.start() else question[modifier.end():start]
    if gap.strip():
        return None  # Only change a date-adjacent qualifier, not a company/sheet name.
    return question[:modifier.start()] + replacement + question[modifier.end():]


def _lookup_question(question):
    match = _PREMISE.search(question)
    if not match:
        return None
    requests = requested_periods(question)
    if len(requests) != 1:
        return None
    # A date, row identifier or threshold must never be removed as an amount.
    if any(start < match.end("amount") and match.start("amount") < end
           for start, end, *_ in calendar_mentions(question)):
        return None
    target = question[:match.start()].rstrip(" =:,\t")
    remaining = target
    for start, end, *_ in reversed(calendar_mentions(target)):
        remaining = remaining[:start] + " " * (end - start) + remaining[end:]
    if re.search(_NUMBER, remaining):
        return None
    return target + " 얼마야?"
