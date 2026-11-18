"""Korean display names for a workbook's own labels, asked once per workbook.

Prose shows headers, row names, units and captions in Korean. Rather than a word list fitted
to particular files, the labels a report actually shows are collected in a first, offline pass
and read by one bounded model call; each reading is kept by its exact source text. A label with
no reading, or any failure, leaves the source text as it is. Readings only rename what is shown:
the values, references and selections never depend on them.
"""
import asyncio
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar

from app.services.insights.display.label_prompt import SYSTEM as _SYSTEM

MAX_LABELS, MAX_LENGTH, CHUNK, MAX_CONTEXT = 600, 160, 150, 6
_READINGS: dict[str, str] = {}
_COUNTERS: dict[str, str] = {}
_COLLECTED: ContextVar[set | None] = ContextVar("collected_labels", default=None)
_PREPARED: set[str] = set()
_COUNTER_WORDS = {"people": "명", "households": "가구", "cases": "건", "things": "개"}


def reading(text):
    """The Korean reading of an exact source label, or None; a collecting pass records the label."""
    key = " ".join(str(text or "").split())
    if not key or len(key) > MAX_LENGTH or re.search(r"[가-힣]", key) or not re.search(r"[A-Za-z]", key):
        return None
    if (collected := _COLLECTED.get()) is not None:
        collected.add(key)
    return _READINGS.get(key.casefold())


def counter(text):
    """The Korean counter word ("명") a measure label's numbers are counted in, or "".

    A collecting pass records the label as a measure, so only measures are asked what they count.
    """
    key = " ".join(str(text or "").split())
    if (collected := _COLLECTED.get()) is not None:
        collected.measures.add(key)
    return _COUNTERS.get(key.casefold(), "")


class _Found(set):
    def __init__(self):
        super().__init__()
        self.measures = set()


@contextmanager
def collecting():
    found = _Found()
    token = _COLLECTED.set(found)
    try:
        yield found
    finally:
        _COLLECTED.reset(token)


def prepare_labels(key, render, translator=None, context=()):
    """Run ``render`` once to see which labels it shows, then read the unread ones in one call.

    ``key`` identifies the workbook so a process asks once per workbook; ``render`` is offline.
    ``context``: the workbook's own names (file, sheets), which say what field its labels belong to.
    """
    if key in _PREPARED:
        return
    with collecting() as found:
        render()
    missing = sorted(label for label in found if label.casefold() not in _READINGS)[:MAX_LABELS]
    if missing:
        translator = translator or LangChainLabelTranslator.from_environment()
        if translator is None:
            return  # no model configured: labels stay as written, and a later call may still read them
        try:
            readings = asyncio.run(translator.translate(missing, list(context), found.measures))
        except Exception:
            return
        for label, read in readings.items():
            korean, unit = read if isinstance(read, tuple) else (read, "")
            if isinstance(korean, str) and korean.strip() and len(korean) <= MAX_LENGTH:
                _READINGS[label.casefold()] = korean
                if isinstance(unit, str) and re.fullmatch(r"[가-힣]{1,3}", unit.strip()):
                    _COUNTERS[label.casefold()] = unit.strip()
    _PREPARED.add(key)


class LangChainLabelTranslator:
    def __init__(self, api_key, model, timeout):
        self._api_key, self._model, self._timeout = api_key, model, timeout

    @classmethod
    def from_environment(cls):
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        found = LangChainSourceLabelResolver.from_environment()
        return cls(found._api_key, found._model, found._timeout) if found else None

    async def translate(self, labels, context=(), measures=()):
        self._labels, self._context = list(labels), [str(name)[:MAX_LENGTH] for name in context][:MAX_CONTEXT]
        self._measures = set(measures)
        chunks = [labels[start:start + CHUNK] for start in range(0, len(labels), CHUNK)]
        parts = await asyncio.gather(*(self._chunk(chunk) for chunk in chunks))
        return {label: korean for part in parts for label, korean in part.items()}

    async def _chunk(self, labels):
        import httpx
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
        from typing import Literal

        from pydantic import BaseModel, ConfigDict, Field

        from app.agent.query.intent_classifier import _sampling

        class Item(BaseModel):
            model_config = ConfigDict(extra="forbid")
            id: int
            korean: str
            counts: Literal["people", "households", "cases", "things", "none"] = Field(description="Rule 5")

        class Readings(BaseModel):
            model_config = ConfigDict(extra="forbid")
            items: list[Item]

        async with httpx.AsyncClient(timeout=max(self._timeout, 30.0)) as client:
            model = ChatOpenAI(model=self._model, api_key=self._api_key, timeout=max(self._timeout, 30.0), max_retries=0,
                               max_completion_tokens=6000, http_async_client=client, **_sampling())
            # The workbook's own names and its longest labels (its captions) say what field the short ones belong to.
            context = self._context + sorted(self._labels, key=len, reverse=True)[:MAX_CONTEXT]
            result = await model.with_structured_output(Readings, method="json_schema").ainvoke([
                SystemMessage(content=_SYSTEM),
                HumanMessage(content=json.dumps({"context_captions": context, "labels": [
                    {"id": number, "label": label, "measure": label in self._measures}
                    for number, label in enumerate(labels)]}, ensure_ascii=False))])
        items = Readings.model_validate(result).items
        return {labels[item.id]: (item.korean.strip(), _COUNTER_WORDS.get(item.counts, ""))
                for item in items if 0 <= item.id < len(labels)}
