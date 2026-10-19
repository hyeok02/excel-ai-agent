"""Source-bound descriptions of distinct counts, shares and per-group ranks."""
import re

from app.agent.query.tabular_request_grouping import _source_tokens, _quoted_sources
from app.agent.query.tabular_request_literals import without_literals

DISTINCT = re.compile(r"중복\s*(?:을\s*)?(?:제거|제외)|중복\s*없이|고유|\b(?:distinct|unique|deduplicated)\b", re.I)
SHARE = re.compile(r"비중|기여율|점유율|\b(?:share|contribution)\b", re.I)
COUNT = re.compile(r"건수|개수|인원수|행\s*수|레코드\s*수|(?<![가-힣])수(?=$|\s|[?!.]|는|가|를)|몇\s*(?:개|건|명)|\b(?:count|number)\b", re.I)


def advanced_operations_match(text, plan, table):
    if not hasattr(plan, "group_by"):
        return not DISTINCT.search(text) and not SHARE.search(text)
    masked, identifiers = _source_tokens(text, table)
    if masked is None:
        return not (getattr(plan, "share_of_total", False) or plan.operation == "distinct_count")
    distinct = bool(DISTINCT.search(masked))
    share = bool(SHARE.search(masked))
    if distinct != (plan.operation == "distinct_count") or share != plan.share_of_total:
        return False
    if distinct and (not COUNT.search(masked) or not _distinct_fields(masked, plan, identifiers)):
        return False
    if share:
        # A changed denominator is a separate population query, not this DSL.
        if plan.filters and re.search(r"전체\s*원본|필터\s*(?:와|에)?\s*관계\s*없이", masked, re.I):
            return False
        valid_measure = ((plan.operation == "numeric_summary" and plan.statistic == "sum"
                          and len(plan.column_ids) == 1)
                         or (plan.operation == "row_count" and not plan.column_ids))
        if (not plan.group_by or not valid_measure or re.search(
                    r"필터\s*(?:전|무시)|조건\s*(?:전|무시|없이)|선택\s*전|전체\s*(?:파일|시트)|"
                    r"\b(?:unfiltered|before\s+filter|ignore\s+filters?|all\s+sheets?)\b", masked, re.I)):
            return False
    per = getattr(plan, "per_group_limit", None)
    explicit_per = bool(re.search(r"각\s*§\d+§|§\d+§\s*(?:마다|별)|\b(?:per|each)\s+§\d+§", masked, re.I))
    if per is not None and (plan.operation != "row_list" or not plan.group_by or not explicit_per):
        return False
    if per is not None and re.search(r"\d+\s*명|\b(?:people|persons?|employees?)\b", masked, re.I):
        identities = set(plan.identity_column_ids)
        if (not identities or not identities <= set(plan.column_ids)
                or identities & (set(plan.group_by) | {plan.order_by})):
            return False
    if plan.operation == "row_list" and plan.group_by and per is None:
        return False
    return True


def _distinct_fields(text, plan, identifiers):
    # Field names are discovered from this source; no customer/entity glossary.
    token = r"§\d+§"
    keys = rf"{token}(?:\s*(?:,|·|/|및|와|과|and\b|&)\s*{token})*"
    named = set()
    for marker in DISTINCT.finditer(text):
        before, after = text[:marker.start()], text[marker.end():]
        patterns = [re.match(rf"\s*(?:한|된|의|of\b)?\s*(?:(?:count|combinations?)\s+(?:of\s+)?)?\(?({keys})", after, re.I),
                    re.search(rf"({keys})\)?\s*(?:조합\s*)?(?:의|을|를)?\s*$", before, re.I)]
        for match in patterns:
            if match:
                named.update(identifiers[int(number)] for number in re.findall(r"§(\d+)§", match.group()))
    return bool(named) and named == set(plan.column_ids) and 1 <= len(plan.column_ids) <= 3


def categorical_request_text(text, plan, original=None, table=None):
    if original is not None and table is not None:
        sources = _quoted_sources(original, table)
        for match in re.finditer(r"'[^']*'|\"[^\"]*\"|‘[^’]*’|“[^”]*”", original):
            if sources[match.start():match.end()].strip() == match.group()[1:-1]:
                text = text[:match.start()] + " " + text[match.start() + 1:match.end() - 1] + " " + text[match.end():]
    if plan.operation != "distinct_count":
        return text
    for marker in reversed(list(DISTINCT.finditer(without_literals(text)))):
        suffix = re.match(r"(?:한|된)?", text[marker.end():]).end()
        end = marker.end() + suffix
        text = text[:marker.start()] + " " * (end - marker.start()) + text[end:]
    return text
