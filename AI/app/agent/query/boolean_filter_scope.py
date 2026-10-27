"""Certify logical structure before reusing ordinary output/scope validators."""
import re

from app.agent.query.boolean_filter_language import boolean_question, expression_key, parse_boolean
from app.agent.query.boolean_filter_models import validate_expression
from app.agent.query.tabular_request_literals import without_literals


def checked_boolean_request(question, plan, table, tables):
    expression = getattr(plan, "filter_expression", None)
    if expression is None and not boolean_question(question):
        return None
    if expression is None:
        return False  # Legacy filtering has no three-valued NOT/OR execution contract.
    # The relational adapter has no boolean execution contract. Do not turn a
    # source question into a joined flat-AND plan by validating leaves alone.
    if not hasattr(plan, "filter_expression"):
        return False
    parsed = parse_boolean(question, table)
    if parsed is None:
        return False
    try:
        validate_expression(expression, len(plan.filters))
        if expression_key(expression, plan.filters) != expression_key(parsed.expression, parsed.filters):
            return False
    except (ValueError, IndexError):
        return False
    if not remaining_scope_supported(parsed.remainder, table, tables):
        return False
    return parsed.remainder


def remaining_scope_supported(text, table, tables):
    # The new grammar must not silently drop an unknown extra condition. Keep
    # this bounded output vocabulary explicit; original validators still check
    # operation, metric, grouping, rankings, units and all source scopes.
    names = {column.header for column in table.columns}
    names |= {item.sheet_name for item in tables}
    names |= {value for item in tables for _, value in item.context if isinstance(value, str)}
    for name in sorted(names, key=len, reverse=True):
        text = re.sub(re.escape(name), " ", text, flags=re.I)
    text = re.sub(r"(?:'[^']+'|[\w .-]+)!\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?", " ", text, flags=re.I)
    if without_literals(text) != text:  # Unbound quoted values are not output instructions.
        return False
    text = re.sub(r"(?:상위|하위|앞의|처음|top|bottom|first)\s*\d+", " ", text, flags=re.I)
    # Output question endings carry no population constraint. Consume complete
    # counting phrases before smaller particles (이/야) can split their meaning.
    text = re.sub(r"몇\s*(?:건|개|명|곳|행|가지)(?:이야|야|인가요|인지|입니까|이니)?", " ", text)
    words = r"조건|해당하는|해당|만족하는|만족|맞는|대상|중에서|중|행|레코드|기록|항목|거래|장비|건|개|명|곳|수|"
    words += r"합계|총합|총액|합산|평균|최솟값|최댓값|최소값|최대값|목록|값|건수|개수|몇|얼마|알려줘|보여줘|계산해줘|구해줘|구해|"
    words += r"시트|표|범위|그룹|별로|별|각|마다|전체|모두|각각|기준|으로|에서|에게|대한|대해|의|을|를|이|가|은|는|인|와|과|에|만|"
    words += r"\b(?:where|with|of|the|a|an|in|rows?|records?|items?|transactions?|count|number|how|many|what|is|are|"
    words += r"sum|total|average|mean|minimum|maximum|values?|list|show|give|calculate|please|by|per|each|sheet|table|all)\b"
    text = re.sub(words, " ", text, flags=re.I)
    return not re.sub(r"[\s,;:.?!'\"·_-]", "", text)
