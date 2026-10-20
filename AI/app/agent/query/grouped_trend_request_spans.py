"""Consume only source-bound grouping and condition spans, never free text."""
import re

from app.agent.query.tabular_request_literals import source_headers

_JOIN = re.compile(r"\s*(?:,|·|/|와|과|및|하고|and|&)\s*", re.I)
_BRIDGE = re.compile(r"[\s:'\"‘’“”=]*(?:(?:이|가|은|는|의|값|상태|아닌|제외|포함된|포함한|포함|만|인)|"
                     r"(?:is|are|not|equals?|contains?|value|status)\b|[\s:'\"‘’“”=])*", re.I)
_TAIL = re.compile(r"\s*(?:(?:이|가)\s*)?(?:아닌|제외|외의|포함된|포함한|포함|인)?"
                   r"(?:\s*(?:행|레코드|기간|시점|조건))?(?:만|에서|의|에|을|를|은|는)?"
                   r"(?![가-힣A-Za-z0-9_])")


def headers_for(question, table):
    headers = source_headers(question, table)
    return sorted(headers, key=lambda item: item[1].start())


def grouping_spans(question, headers):
    groups, spans = [], []
    for position, (column, match) in enumerate(headers):
        suffix = re.match(r"\s*별", question[match.end():])
        prefix = re.search(r"\b(?:group(?:ed)?\s+)?by\s*$", question[:match.start()], re.I)
        if suffix:
            chain, start = [column], match.start()
            for prior, previous in reversed(headers[:position]):
                if previous.end() <= start and _JOIN.fullmatch(question[previous.end():start]):
                    chain.insert(0, prior)
                    start = previous.start()
                else:
                    break
            groups.extend(chain)
            spans.append((start, match.end() + suffix.end()))
        elif prefix:
            chain, end = [column], match.end()
            for following, next_match in headers[position + 1:]:
                if _JOIN.fullmatch(question[end:next_match.start()]):
                    chain.append(following)
                    end = next_match.end()
                else:
                    break
            groups.extend(chain)
            spans.append((prefix.start(), end))
    return tuple(dict.fromkeys(groups)), spans


def adjacent_headers(question, start, end, headers):
    candidates = []
    for column, header in headers:
        if header.end() <= start:
            gap = question[header.end():start]
        elif end <= header.start():
            gap = question[end:header.start()]
        else:
            continue
        if len(gap) <= 40 and _BRIDGE.fullmatch(gap):
            candidates.append((len(gap), column, header))
    distance = min((value[0] for value in candidates), default=None)
    return [(column, header) for gap, column, header in candidates if gap == distance]


def with_tail(question, span):
    start, end = span
    suffix = _TAIL.match(question[end:])
    return start, end + (suffix.end() if suffix else 0)


def erase_spans(question, spans):
    characters = list(question)
    for start, end in spans:
        characters[start:end] = " " * (end - start)
    return "".join(characters)
