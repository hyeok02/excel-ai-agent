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
    return [word for word in candidate_words(question, SimpleNamespace(columns=())) if re.search(r"[가-힣]", word)]


def named_topic(words, topics, resolver=None):
    """(word, topic, resolver) when the words name exactly one topic, else None."""
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
    # "발전량" inside "석탄 발전량" is the wider name: the phrase naming another series is the more specific.
    named = [(word, topic) for word, topic in named
             if not any(word != other and word in other and topic != other_topic for other, other_topic in named)]
    named = [(word, topic) for word, topic in named if not any(word != other and other in word for other, _ in named)]
    if len({topic for _, topic in named}) != 1:
        return None
    return (*named[0], resolver)


async def _read(resolver, words, topics):
    return await asyncio.gather(*(resolver.resolve(word, "data series", topics) for word in words))
