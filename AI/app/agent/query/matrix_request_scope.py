"""A proved matrix intersection cannot erase an unbound entity or condition."""
import re

from app.agent.query.references import REFERENCE_PATTERN, extract_references

_LOOKUP_ENGLISH = re.compile(r"\b(?:what|is|the|value|of|in|on|for|please|tell|me|how|much)\b", re.I)
_LOOKUP_KOREAN = re.compile(r"(?:알려\s*줘|알려주세요|보여\s*줘|얼마(?:인가요|입니까|인지|야)?|값|시트|에서|기준(?:으로)?|"
                            r"(?:의|은|는|이|가|을|를)(?=\s|[?？.!,:;]|$))")
_INTERPRETATION = re.compile(r"\b(?:why|reason|cause|explain|normal)\b|왜|이유|원인|정상|의미", re.I)
_INTERPRETATION_WORDS = re.compile(
    r"\b(?:why|reason|cause|explain|normal|increase|increased|decrease|decreased|did|it|whether)\b|"
    r"왜|이유|원인|정상인지|정상|의미|증가한|감소한|설명해\s*줘|설명해주세요", re.I)


def plain_matrix_lookup(question, proof):
    remainder = _remainder(question, proof, direct=False)
    return remainder is not None and not _compact(remainder)


def matrix_request_supported(question, proof):
    remainder = _remainder(question, proof, direct=True)
    if remainder is None:
        return False
    if not _compact(remainder):
        return True
    # A known request for interpretation may retain a literal source
    # observation, but no unexplained company, country, filter, or arithmetic.
    return bool(_INTERPRETATION.search(remainder)) and not _compact(
        _LOOKUP_KOREAN.sub(" ", _INTERPRETATION_WORDS.sub(" ", remainder)))


def mentioned_matrix_sheets(question, proof):
    axes = (str(proof["row_value"]).casefold(), str(proof["column_value"]).casefold())
    names = proof.get("sheet_names", [proof["sheet"]])
    named = set()
    for name in names:
        escaped = re.escape(name.casefold())
        explicit = any(pattern.search(question.casefold()) for pattern in _sheet_patterns(escaped))
        # A metric/period word that also names a sheet is not a sheet selector.
        bare = not any(name.casefold() in axis for axis in axes) and re.search(
            rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])", question.casefold())
        if explicit or bare:
            named.add(name)
    return named


def _remainder(question, proof, *, direct):
    rest = question.casefold()
    names = mentioned_matrix_sheets(question, proof)
    for name in names:
        for pattern in _sheet_patterns(re.escape(name.casefold())):
            rest = pattern.sub(" ", rest)
    addressed = direct and bool(extract_references(question))
    rest = REFERENCE_PATTERN.sub(" ", rest)
    for value in (proof["row_value"], proof["column_value"]):
        label = str(value).strip().casefold()
        if label not in rest and not addressed:
            return None
        rest = rest.replace(label, " ")
    for name in names:
        rest = rest.replace(name.casefold(), " ")
    return _LOOKUP_KOREAN.sub(" ", _LOOKUP_ENGLISH.sub(" ", rest))


def _sheet_patterns(escaped):
    return (
        re.compile(rf"(?<![A-Za-z0-9_])(?:in|on|from|using)\s+(?:the\s+)?(?:sheet\s+)?['\"]?{escaped}['\"]?(?![A-Za-z0-9_])"),
        re.compile(rf"(?<![A-Za-z0-9_])['\"]?{escaped}['\"]?\s*(?:에서|시트(?:\s*기준)?|sheet(?:\s*기준)?)(?![A-Za-z0-9_])"),
    )


def _compact(text):
    return re.sub(r"[\s?？.!,:;'\"‘’“”()]+", "", text)
