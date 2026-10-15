"""Read explicit categorical predicates even when no source row has the value."""
import re

_PREFIX = re.compile(
    r"^\s*(?:(?P<operator>is\s+not|are\s+not|not\s+equal\s+to|!=|≠|"
    r"contains?|includes?|is|are|equals?|=|에\s*포함된|에\s*포함한|포함)\s*|"
    r"(?:(?:이|가|은|는|의|에|값|표시|상태)\s*)*)(?P<body>.*)$", re.I,
)
_SUFFIX = re.compile(
    r"^(?P<value>.+?)\s*(?P<operator>[이가]\s*(?:아닌|포함된|포함한)|아닌|제외|외의|포함된|포함한|포함|인|이고|이며)"
    r"(?=\s|$)", re.I,
)
_TEXT_END = re.compile(r"[,;?!.]|\b(?:and|or|rows?|records?|count|list|show|please)\b", re.I)


def categorical_predicates(text, headers):
    predicates = []
    for column, header in headers:
        stop = min((other.start() for _, other in headers if other.start() >= header.end()),
                   default=len(text))
        match = _PREFIX.match(text[header.end():stop])
        if match is None:
            continue
        prefix = match.group("operator") or ""
        body = match.group("body")
        quoted = _quoted_value(body)
        suffix = _SUFFIX.match(body) if quoted is None else None
        if quoted is not None:
            raw, remainder = quoted
            # Treat a quoted literal as one value before reading grammar outside
            # its closing quote: punctuation/conjunctions inside it are data.
            suffix = _SUFFIX.match("literal" + remainder)
            if suffix and suffix.group("value").strip() != "literal":
                suffix = None  # Never swallow another literal to find a suffix.
            suffix_operator = suffix.group("operator") if suffix else ""
            if suffix:
                remainder = remainder[suffix.end() - len("literal"):]
        elif suffix:
            raw, suffix_operator = suffix.group("value"), suffix.group("operator")
            remainder = body[suffix.end():]
        elif prefix:
            boundary = _TEXT_END.search(body)
            raw, suffix_operator = body[:boundary.start()].strip() if boundary else body.strip(), ""
            remainder = body[boundary.start():] if boundary else ""
        else:
            if _unsupported_tail(body):
                predicates.append((column, ("unparsed", body), "unsupported_predicate"))
            continue
        if _unsupported_tail(remainder, suffix_operator in {"이고", "이며"}):
            # Never certify only the first condition of an unsupported compound
            # predicate. This sentinel cannot match any valid plan operator.
            predicates.append((column, ("unparsed", remainder), "unsupported_predicate"))
            continue
        value = normalize(raw.strip(" \t'\"‘’“”"))
        # Numeric comparisons, dates and percent scales have a separate parser.
        if not value or len(value) > 300 or re.fullmatch(
            r"[-+]?\d[\d,./:% -]*(?:이상|이하|미만|초과|보다\s*(?:큰|작은))?", value,
        ):
            continue
        prefix_op, suffix_op = _operator(prefix), _operator(suffix_operator)
        if prefix and prefix_op != "equals" and suffix_op not in {"equals", prefix_op}:
            operator = "conflicting_operators"
        else:
            operator = prefix_op if prefix_op != "equals" else suffix_op
        if (value in {"빈칸", "공백", "blank", "empty", "null"}
                and not raw.strip().startswith(("'", '"', "‘", "“"))
                and operator in {"equals", "not_equals"}):
            value, operator = None, "not_blank" if operator == "not_equals" else "is_blank"
        elif value in {"true", "false"} and not raw.strip().startswith(("'", '"', "‘", "“")):
            value = value == "true"
        predicates.append((column, _key(value), operator))
    return predicates


def _unsupported_tail(remainder, conjunctive=False):
    tail = remainder.strip()
    if not tail:
        return False
    if conjunctive:
        return True
    if re.search(r"['\"‘“]", tail):
        return True
    if re.search(r"\b(?:and|or|but|except|excluding|not|without)\b\s+\S|"
                 r"(?:이면서|이거나|또는|혹은|빼고|제외|아닌|포함)\s*\S", tail, re.I):
        return True
    # A separator can terminate a sentence or separate another literal. Only
    # an empty tail or an output request is harmless without another field.
    if tail[0] in ",;.!?":
        rest = tail.lstrip(",;.!? ").strip()
        return bool(rest) and not re.fullmatch(
            r"(?:rows?|records?|count|list|show|please|보여줘|알려줘|목록|건수|개수)[\s?!.]*", rest, re.I)
    return False


def _quoted_value(body):
    body = body.lstrip()
    pairs = {"'": "'", '"': '"', "‘": "’", "“": "”"}
    if not body or body[0] not in pairs:
        return None
    end = body.find(pairs[body[0]], 1)
    if end < 0:
        # An incomplete quoted value must not authorize a shorter predicate.
        return body, ""
    return body[:end + 1], body[end + 1:]


def predicates_match(predicates, plan):
    requested = set(predicates)
    actual = {(item.column_id, _key(item.value), item.operator) for item in plan.filters}
    if not requested <= actual:
        return False
    values = {value for _, value, _ in requested}
    return all(value not in values or (column, value, operator) in requested
               for column, value, operator in actual)


def local_operator(text, start, end, headers):
    before_start = max((header.end() for _, header in headers if header.end() <= start), default=0)
    after_end = min((header.start() for _, header in headers if header.start() >= end), default=len(text))
    before = re.split(r"[,;]", text[before_start:start])[-1]
    after = re.split(r"[,;]", text[end:after_end])[0]
    negative = bool(re.match(r"\s*(?:[이가]\s*)?(?:아닌|아니|제외|외의)", after)
                    or re.search(r"(?:not|except|excluding)\s*$", before, re.I))
    contains = bool(re.search(r"포함|contains?", before[-16:] + after[:10], re.I))
    return "not_equals" if negative else "contains" if contains else "equals"


def _operator(value):
    if re.search(r"not|!=|≠|아닌|제외|외의", value, re.I):
        return "not_equals"
    if re.search(r"contains?|includes?|포함", value, re.I):
        return "contains"
    return "equals"


def normalize(value):
    return " ".join(str(value).casefold().split())


def _key(value):
    return type(value).__name__, normalize(value)
