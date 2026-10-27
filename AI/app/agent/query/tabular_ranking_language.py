"""Bounded source-label grammar for one exact-N numeric ordering request."""
import re
from dataclasses import dataclass

_RANK = re.compile(r"(?P<direction>상위|하위|top|bottom|높은|낮은|큰|작은|highest|lowest|largest|smallest)\s*(?P<count>\d+)", re.I)
_SORT = re.compile(r"오름차순|내림차순|낮은\s*순(?:서)?|높은\s*순(?:서)?|작은\s*순(?:서)?|큰\s*순(?:서)?|\bascending\b|\bdescending\b", re.I)
_COUNT = re.compile(r"(?<![\w.])([1-9]\d*)\s*(?:개|건|행|명|rows?\b|records?\b|items?\b)", re.I)
_TIES = re.compile(r"동점|동률|공동\s*순위|\bties?\b|\bdense\s*rank\b", re.I)
_EXTREME = re.compile(r"(?:가장|제일)\s*(?P<direction>많은|적은|높은|낮은|큰|작은)|"
                      r"\b(?P<english>highest|lowest|largest|smallest)\b(?!\s*\d)", re.I)


@dataclass(frozen=True)
class RankRequest:
    count: int | None
    descending: bool
    metric: str | None


def ranking_request(text, table, *, grouped=False, excluded=()):
    if _TIES.search(text):
        return False
    from app.agent.query.source_measure_labels import bound_header_mentions
    source_mentions = bound_header_mentions(text, table)
    ranks, sorts = list(_RANK.finditer(text)), list(_SORT.finditer(text))
    extremes = [match for match in _EXTREME.finditer(text)
                if not any(rank.start() <= match.start() < rank.end() for rank in ranks)
                and not any(header.start() <= match.start() and header.end() >= match.end()
                            for _, header in source_mentions)]
    if len(ranks) > 1 or len(sorts) > 1 or len(extremes) > 1 or ranks and extremes:
        return False
    if not ranks and not sorts and not extremes:
        return None
    found = ranks[0] if ranks else extremes[0] if extremes else sorts[0]
    direction = (found.group("direction") or found.group("english")) if extremes else (
        found.group("direction") if ranks else found.group())
    descending = _descending(direction)
    if sorts and _descending(sorts[0].group()) != descending:
        return False
    counts = {int(match.group(1)) for match in _COUNT.finditer(text)}
    count = int(found.group("count")) if ranks else 1 if extremes else next(iter(counts), None)
    if len(counts) > 1 or counts and count not in counts:
        return False
    columns = [column for column in table.columns if column.id not in excluded]
    mentions = [(column, match) for column, match in source_mentions
                if column not in excluded]
    preceding = [(match.end(), column) for column, match in mentions
                 if match.end() <= found.start() and found.start() - match.end() < 80]
    metric = max(preceding, default=(0, None))[1]
    if grouped and metric is None:
        named = {column for column, _ in mentions}
        metric = next(iter(named)) if len(named) == 1 else None
    # "top 5 rows by Score" and "Score descending" share one contract.
    after = text[found.end():]
    by = re.search(r"\bby\s+", after, re.I)
    if by:
        candidates = [column.id for column in columns
                      if re.match(re.escape(column.header) + r"(?![A-Za-z0-9_])", after[by.end():], re.I)]
        if len(candidates) != 1 and not grouped:
            return False
        if len(candidates) == 1:
            metric = candidates[0]
    if extremes and metric is None:
        following = {column for column, match in mentions if match.start() >= found.end()
                     and re.fullmatch(r"\s*(?:(?:value|of|for|the)\s+)*", text[found.end():match.start()], re.I)}
        if len(following) != 1:
            return False
        metric = next(iter(following))
    return RankRequest(count, descending, metric)


def _header_matches(header, text):
    return re.finditer(r"(?<![A-Za-z0-9_])" + re.escape(header) + r"(?![A-Za-z0-9_])", text, re.I)


def _descending(direction):
    return direction.casefold().replace(" ", "") in {
        "상위", "top", "높은", "큰", "highest", "largest", "내림차순", "높은순", "높은순서",
        "큰순", "큰순서", "descending", "많은",
    }
