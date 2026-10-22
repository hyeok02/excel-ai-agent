"""Shared language for ranked changes; comparison bases are never interchangeable."""
from dataclasses import dataclass
import re

from app.agent.query.comparison_scope import requested_metric_group

_DOWN = re.compile(r"감소|줄어|줄었|줄은|하락|낙폭|떨어|\b(?:decreas\w*|declin\w*|drop\w*|fell|fall\w*)\b", re.I)
_UP = re.compile(r"증가|늘어|늘었|상승|\b(?:increas\w*|grew|growth|ris\w*|gain\w*)\b", re.I)
_RANK = re.compile(r"가장|제일|최대|최고|순위|많이|큰|\b(?:most|largest|biggest|greatest|rank\w*)\b", re.I)
_GROUP = re.compile(r"부서|부문|직무|역할|항목|지표|\b(?:departments?|roles?|metrics?|categories)\b", re.I)
_NET = re.compile(r"(?:처음|최초|시작).{0,30}(?:마지막|최종|끝)|순\s*(?:증가|감소|증감)|"
                  r"\b(?:net|first.{0,30}last|start.{0,30}end|beginning.{0,30}end)\b", re.I)
_ADJACENT = re.compile(r"직전|인접|연속한|전\s*(?:분기|월|년)\s*(?:대비|보다)|"
                       r"(?:한|단일)\s*(?:구간|기간)|\b(?:consecutive|adjacent|period.over.period)\b", re.I)
_EXTREME = re.compile(r"(?:최고점|최저점|고점|저점|피크|바닥).{0,20}(?:대비|현재|최신|마지막)|"
                      r"\b(?:peak|trough).{0,20}(?:latest|last|current)\b", re.I)
_DRAWDOWN = re.compile(r"최대\s*낙폭|고점.{0,20}(?:이후\s*)?저점|최고점.{0,20}최저점|"
                       r"저점.{0,20}(?:이후\s*)?고점|"
                       r"\b(?:drawdown|peak.to.trough|trough.to.peak)\b", re.I)
_PERCENT = re.compile(r"증가율|감소율|증감률|변화율|퍼센트|백분율|%|"
                      r"\b(?:percentage|percent|rate)\b", re.I)


@dataclass(frozen=True)
class ChangeRankingRequest:
    group: str | None
    direction: str
    basis: str
    percent: bool = False


def parse_change_ranking_request(question):
    down, up = bool(_DOWN.search(question)), bool(_UP.search(question))
    if down == up or not _RANK.search(question) or not _GROUP.search(question):
        return None
    # Explicit start/end language takes precedence over a generic maximum word.
    basis = change_comparison_basis(question)
    return ChangeRankingRequest(requested_metric_group(question),
                                "decrease" if down else "increase", basis,
                                bool(_PERCENT.search(question)))


def change_comparison_basis(question):
    return next((name for name, pattern in (
        ("net", _NET), ("adjacent", _ADJACENT), ("max_drawdown", _DRAWDOWN),
        ("extreme_to_latest", _EXTREME),
    ) if pattern.search(question)), "auto")


def ranking_request_remainder(question, request):
    """Remove only operation grammar, leaving source metrics and filters to bind."""
    text = question
    text = re.sub(r"(?:고점|최고점)\s*(?:대비\s*)?이후\s*(?:저점|최저점)(?:까지)?|"
                  r"(?:저점|최저점)\s*(?:대비\s*)?이후\s*(?:고점|최고점)(?:까지)?", " ", text)
    # Never erase an arbitrary span between e.g. "처음" and "마지막": that
    # could silently discard a population/filter placed between those words.
    text = re.sub(r"최고점|최저점|고점|저점|피크|바닥|낙폭|순\s*(?=증가|감소|증감)|"
                  r"직전|인접|연속한|(?:한|단일)\s*(?:구간|기간)|"
                  r"\b(?:net|peak|trough|drawdown|consecutive|adjacent|first|last|"
                  r"start|end|beginning|current|latest)\b", " ", text, flags=re.I)
    # Consume Korean conjugations, not arbitrary text following a direction.
    text = re.sub(r"(?:증가|감소|상승|하락)(?:율|률|량|한|했|했어|했나|했는|하는)?", " ", text)
    text = re.sub(r"(?:줄어든|줄었(?:어|는|던)?|줄은|늘어난|늘었(?:어|는|던)?|떨어진)", " ", text)
    for pattern in (_DOWN, _UP, _RANK, _PERCENT):
        text = pattern.sub(" ", text)
    text = re.sub(r"(?<![가-힣])(?:동안|사이|대비)(?![가-힣])", " ", text)
    text = re.sub(r"(?:전체\s*)?기간\s*(?:동안|중|내)?|시작(?:값)?|마지막(?:값)?|최초(?:값)?|최종(?:값)?|끝(?:값)?|처음|"
                  r"(?:어디|어느|무슨)(?:인가요|입니까|야|가|는|이야)?|"
                  r"비교(?:해서|해줘|해|하면)?|순서대로|알려(?:줘|주세요)?|"
                  r"\b(?:over|the|whole|entire|period|which|what|had|has|was|is|"
                  r"from|to|of|during|compare|show|tell|me|a|an)\b", " ", text, flags=re.I)
    return text
