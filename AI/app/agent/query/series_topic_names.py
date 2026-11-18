"""Read which series a question names among every series name the report can state.

"석탄 발전량" names 'Coal'; "발전량" inside it names the wider total and does not compete.
Exactly one series must be named; the reading is stated by the caller with its answer.
"""
import asyncio
import re
from types import SimpleNamespace

from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.tabular_translated_filters import candidate_words


def series_words(question):
    # A clarification's follow-up ("'Sheet'!B13:AL74 범위의 H열 X 기준으로: 질문") is read for its question part,
    # so the scope's names take no word slot; any other wording is read whole.
    asked = question.split("기준으로:", 1)[1] if _SCOPED.match(question) and "기준으로:" in question else question
    asked = _SCOPED.sub(" ", asked)
    return [word for word in candidate_words(asked, SimpleNamespace(columns=())) if re.search(r"[가-힣]", word)]


_DESCRIPTIVE = re.compile(r"연간|연도별|월별|분기별|일별|누적|최근|올해|작년|전년|평균|합계|총|전체|국내|해외|월간|연말|연초")
_SCOPED = re.compile(r"^\s*'?[^!\n]*?'?![A-Z$]+\d+(?::[A-Z$]+\d+)?\s*범위(?:의|에서)?")


def named_topic(words, topics, resolver=None):
    """(word, topic, resolver) when the words name exactly one topic, (word, None, resolver) when a word
    specifying the named measure names no series, else None."""
    if not topics or not words:
        return None
    if resolver is None:
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        resolver = LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return None
    try:
        results = asyncio.run(_read(resolver, words, topics))
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None
    named = [(word, topics[result.candidate_id]) for word, result in zip(words, results)
             if result.status == "resolved" and type(result.candidate_id) is int and 0 <= result.candidate_id < len(topics)]
    # "풍력 발전량": 발전량 names the total, but 풍력, what it specifies, names no series at all. The total
    # is not what was asked: (풍력, None) says which word the source has no series for.
    read = {word for word, _ in named}
    for phrase in (word for word in words if " " in word and word not in read):
        *parts, head = phrase.split()
        if head in read and (missing := [part for part in parts if part not in read and not _DESCRIPTIVE.fullmatch(part)]):
            return missing[0], None, resolver
    # "발전량" inside "석탄 발전량" is the wider name: the phrase naming another series is the more specific.
    named = [(word, topic) for word, topic in named
             if not any(word != other and word in other and topic != other_topic for other, other_topic in named)]
    # Korean names its head last: in "태양광 발전량" the measure 발전량 is what 태양광 specifies, so it is
    # not a second series even when the phrase as a whole fits several (Solar, Solar Photovoltaic).
    heads = {phrase.split()[-1] for phrase in words if " " in phrase
             and any(part != phrase.split()[-1] and topic != head_topic for part, topic in named if part in phrase.split()[:-1]
                     for head, head_topic in named if head == phrase.split()[-1])}
    named = [(word, topic) for word, topic in named if word not in heads]
    named = [(word, topic) for word, topic in named if not any(word != other and other in word for other, _ in named)]
    if len({topic for _, topic in named}) != 1:
        return None
    return (*named[0], resolver)


async def _read(resolver, words, topics):
    return await asyncio.gather(*(resolver.resolve(word, "data series", topics) for word in words))
