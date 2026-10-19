"""Check explicit source dimensions independently from model-selected measures."""
import re

from app.agent.query.ambiguity_labels import label_base

_TOKEN = r"§\d+§"
_JOIN = r"\s*(?:,|·|/|및|와|과|하고|and\b|&)\s*"
_KEYS = rf"{_TOKEN}(?:\s*별)?(?:{_JOIN}{_TOKEN}(?:\s*별)?)*"
_KOREAN = re.compile(rf"{_KEYS}\s*별", re.I)
_ENGLISH = re.compile(rf"\b(?:group(?:ed)?\s+)?by\s+{_KEYS}", re.I)
_PER = re.compile(rf"(?:각\s*{_KEYS}\s*(?:에서|내에서|마다)|{_KEYS}\s*마다|\b(?:per|each)\s+{_KEYS})", re.I)
_STAT = r"합계|총합|평균|최솟값|최댓값|최소값|최대값|건수|개수|\b(?:sum|total|average|mean|minimum|maximum|count)\b"
_UNSUPPORTED = re.compile(
    r"비율|증감률|증가율|\b(?:ratio|growth)\b|"
    r"중앙값|분산|표준\s*편차|누적|누계|\b(?:median|variance|stddev|cumulative|running)\b|"
    r"나누[어기]|나눈|\b(?:divide|divided|per\s+capita)\b", re.I,
)


def grouping_constraints_match(text, plan, table):
    # Relational plans have their own two-source dimension validator.
    if not hasattr(plan, "group_by"):
        return True
    grouped = list(plan.group_by)
    if len(grouped) != len(set(grouped)) or not set(grouped) <= {c.id for c in table.columns}:
        return False
    masked, identifiers = _source_tokens(text, table)
    if masked is None:
        return not grouped and not re.search(r"별|\b(?:group(?:ed)?\s+)?by\b", text, re.I)
    spans = list(_KOREAN.finditer(masked)) + list(_PER.finditer(masked))
    # In a row-list request, "top 5 by Score" describes ordering, not grouping.
    if plan.operation != "row_list" and (grouped or plan.operation in {"numeric_summary", "row_count", "distinct_count"}):
        spans.extend(_ENGLISH.finditer(masked))
    requested = {identifiers[int(number)] for span in spans
                 for number in re.findall(r"§(\d+)§", span.group())}
    if not grouped:
        return not requested or (plan.operation == "frequencies"
                                  and requested <= set(plan.column_ids))
    if plan.operation not in {"numeric_summary", "row_count", "distinct_count", "row_list"} or requested != set(grouped):
        return False
    if plan.operation == "numeric_summary" and set(grouped) & set(plan.column_ids):
        return False
    if plan.operation == "row_count" and set(plan.column_ids) - set(grouped):
        return False
    if plan.operation == "row_count" and (not re.search(
            r"건수|개수|인원수|행\s*수|레코드\s*수|몇\s*(?:개|건|명)|\bcount\b", masked, re.I)
            or re.search(r"합계|총합|평균|최솟값|최댓값|\b(?:sum|average|mean|minimum|maximum)\b", masked, re.I)):
        return False
    remaining = masked
    for span in sorted(spans, key=lambda match: match.start(), reverse=True):
        tail = masked[span.end():]
        if re.match(_JOIN + r"[^§\s]", tail, re.I):
            return False
        remaining = remaining[:span.start()] + " " * (span.end() - span.start()) + remaining[span.end():]
    if re.search(r"\b(?:group(?:ed)?\s+)?by\b|[^\s§]+별", remaining, re.I) and plan.operation != "row_list":
        return False
    if _UNSUPPORTED.search(masked) or _derived_request(masked):
        return False
    if plan.operation == "numeric_summary" and not _measures_match(remaining, plan, identifiers):
        return False
    return True


def _derived_request(text):
    for statistic in re.finditer(_STAT, text, re.I):
        after = text[statistic.end():]
        if re.match(r"\s*(?:의|에서|을|를)?\s*(?:[+*/×÷-]\s*(?:\d|§)|"
                    r"\d+(?:\.\d+)?\s*(?:%|퍼센트|배|percent\b))", after, re.I):
            return True
        if re.search(r"더해|더하|빼줘|빼고|뺀|차감|곱해|곱하|두\s*배|세\s*배|절반|"
                     r"\b(?:multiply|multiplied|subtract|subtracted|deduct|double|twice|half)\b", after, re.I):
            return True
    return False


def _measures_match(text, plan, identifiers):
    keys = rf"{_TOKEN}(?:{_JOIN}{_TOKEN})*"
    measures = set()
    operation = _STAT + (r"|요약|통계|\bsummary\b|\bstatistics\b" if plan.statistic == "all" else "")
    if getattr(plan, "share_of_total", False):
        operation += r"|비중|기여율|점유율|\b(?:share|contribution)\b"
    for statistic in re.finditer(operation, text, re.I):
        before = re.search(rf"({keys})\s*(?:(?:의|을|를)\s*)?$", text[:statistic.start()], re.I)
        after = re.match(rf"\s*(?:of\s+)?(?:전체\s*|total\s+)?({keys})", text[statistic.end():], re.I)
        for match in (before, after):
            if match:
                measures.update(identifiers[int(number)] for number in re.findall(r"§(\d+)§", match.group()))
    return bool(measures) and measures == set(plan.column_ids)


def _source_tokens(text, table):
    text = _quoted_sources(text, table)
    matches = []
    for position, column in enumerate(table.columns):
        for label in {column.header, label_base(column.header)}:
            if label:
                pattern = r"(?<![\w])" + re.escape(label) + r"(?![A-Za-z0-9_])"
                matches.extend((match.start(), match.end(), position) for match in re.finditer(pattern, text, re.I))
    matches = set(matches)
    matches = [item for item in matches if not any(
        other[0] <= item[0] and item[1] <= other[1] and other[:2] != item[:2] for other in matches)]
    if len({(start, end) for start, end, _ in matches}) != len(matches):
        return None, {}
    for start, end, position in sorted(matches, reverse=True):
        text = text[:start] + f"§{position}§" + text[end:]
    return text, {position: column.id for position, column in enumerate(table.columns)}


def _quoted_sources(text, table):
    names = {label.casefold() for column in table.columns for label in (column.header, label_base(column.header))}

    def substitute(match):
        before, after = text[:match.start()], text[match.end():]
        value = match.group()[1:-1]
        predicate = re.search(r"(?:=|\b(?:is|equals?|contains?|not))\s*$", before, re.I)
        field = re.search(rf"\bby\s*$|(?:{_STAT})\s*(?:of\s*)?$", before, re.I) or re.match(
            rf"\s*(?:별|(?:의\s*)?(?:{_STAT})|요약|통계)", after, re.I)
        return " " + value + " " if value.casefold() in names and field and not predicate else " " * len(match.group())

    return re.sub(r"'[^']*'|\"[^\"]*\"|‘[^’]*’|“[^”]*”", substitute, text)
