"""Bind explicit qualifiers found in source labels, never infer units or periods."""
import re
import unicodedata
from collections import defaultdict

from app.agent.query.ambiguity_labels import normalize_label, source_mentioned, unit_qualifier

_CONVERSION = re.compile(r"환산|변환|제외|아닌|\b(?:convert\w*|exchange|except|excluding|not)\b", re.I)
_CURRENCIES = {"usd", "eur", "krw", "jpy", "gbp", "cad", "aud", "cny", "inr"}
_MAGNITUDES = {"million", "billion", "thousand", "백만", "십억", "천", "000"}


def explicit_column_ids(question):
    korean = re.findall(r"(?<![\w])([A-Z]{1,3})\s*열(?:의|에서|은|는|을|를)?(?![\w])", question, re.I)
    english = [quoted or plain for quoted, plain in re.findall(
        r"(?i:\bcolumn)\s+(?:['\"]([A-Za-z]{1,3})['\"]|([A-Z]{1,3}|[a-z]))(?![\w])", question)]
    return {column.upper() for column in [*korean, *english]}


def qualified_labels(question, labels):
    """Narrow one metric's alternatives only by explicit source annotations.

    A qualifier appearing in several candidate headers deliberately preserves
    all those candidates. No chosen model field, exchange rate, or year default
    is evidence of the user's intended source.
    """
    labels = set(labels)
    if _CONVERSION.search(question):
        return labels
    groups = defaultdict(set)
    for label in labels:
        base = re.sub(r"\(([^()]*)\)|\[([^\[\]]*)\]", lambda match:
                      "" if _qualifier_value(match[1] or match[2]) else match[0],
                      unicodedata.normalize("NFKC", str(label)))
        groups[normalize_label(base)].add(label)
    return set().union(*(_narrow(question, group) for group in groups.values())) if groups else set()


def _narrow(question, labels):
    qualifiers = {label: _qualifiers(label) for label in labels}
    vocabulary = set().union(*qualifiers.values()) if qualifiers else set()
    requested = {token for token in vocabulary if _mentioned(token, question)}
    if not requested:
        return labels
    dimensions = (_CURRENCIES, _MAGNITUDES, {token for token in vocabulary if token.isdigit() and len(token) == 4})
    if any(len(requested & dimension) > 1 for dimension in dimensions):
        return labels
    # All explicit dimensions must agree. Sharing "million" is not enough to
    # choose EUR millions when USD millions was requested.
    selected = {label for label, tokens in qualifiers.items() if requested <= tokens}
    return selected or labels


def _qualifiers(label):
    text = unicodedata.normalize("NFKC", str(label))
    tokens = set()
    for first, second in re.findall(r"\(([^()]*)\)|\[([^\[\]]*)\]", text):
        value = (first or second).strip()
        if re.fullmatch(r"(?:19|20)\d{2}", value):
            tokens.add(value)
        elif unit_qualifier(value):
            tokens.update(_unit_token(token) for token in re.findall(r"[A-Za-z]+|[%$€£₩¥]|백만|십억|천|원|명|건|000", value)
                          if token.casefold() != "in")
    return tokens


def _qualifier_value(value):
    return re.fullmatch(r"(?:19|20)\d{2}", value.strip()) or unit_qualifier(value)


def _mentioned(token, question):
    if re.fullmatch(r"(?:19|20)\d{2}", token):
        return bool(re.search(r"(?<![\w-])(?:FY\s*)?" + token
                              + r"(?:년도?)?(?:과|와|의|은|는|부터|까지|에서)?(?![\w-])", question, re.I))
    # Bare single-letter magnitude markers are too easily confused with
    # source coordinates, table names or record IDs. Full headers still work.
    return len(token) > 1 and (source_mentioned(token, question)
                              or token in {"million", "billion", "thousand"}
                              and source_mentioned(token + "s", question))


def _unit_token(token):
    token = token.casefold()
    return token[:-1] if token in {"millions", "billions", "thousands"} else token


def requested_units_match(question, selected_headers):
    """Raw aggregation has no exchange-rate or unit-conversion executor."""
    if not selected_headers:
        return True
    if re.search(r"환산|변환|\b(?:convert\w*|exchange\s+rate)\b", question, re.I):
        return False
    requested = {unit for unit in _CURRENCIES | _MAGNITUDES if _mentioned(unit, question)}
    if not requested:
        return True
    # Even a single source field must satisfy an explicit currency/scale.
    # Unknown requested units never become an implicit currency conversion.
    return all(requested <= _qualifiers(header) for header in selected_headers)
