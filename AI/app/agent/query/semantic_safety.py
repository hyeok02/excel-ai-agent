"""A vocabulary overlap is necessary, never proof of a predicate or its polarity."""
import re

from app.agent.query.answer_clauses import clauses

UNPROVEN_PREDICATE = re.compile(
    r"같은|같습니다|동일|똑같|다릅|다른|원인|때문|영향|의미합니다|뜻합니다|"
    r"안정적|정상입|정상적|성공|실패|완료|불량|아닙|아니라|없습니다|"
    r"가장|제일|최대|최소|최고|최저|\b(?:same|different|identical|because|caus\w*|"
    r"stable|normal|success\w*|fail\w*|completed|not|never|no|highest|lowest|largest|smallest)\b", re.I
)
QUOTED = re.compile(r"‘([^’]*)’|\"([^\"]*)\"|`([^`]*)`")
DATE = re.compile(r"((?:19|20)\d{2})(?:[-/](\d{1,2})(?:[-/](\d{1,2}))?|"
                  r"\s*년(?:\s*(\d{1,2})\s*월)?(?:\s*(\d{1,2})\s*일)?)")


def semantic_claim_supported(text, evidence, verified_facts):
    normalized = _normal(text)
    # Exact, already verified propositions can be reused, not arbitrary sentences
    # assembled from their vocabulary (especially a negated or reversed version).
    if any(normalized == _normal(part) for fact in verified_facts for part in clauses(fact)):
        return True
    literals = [str(item.value) for item in evidence if getattr(item, "value", None) is not None]
    quoted = [next(value for value in match if value) for match in QUOTED.findall(text) if any(match)]
    prose = QUOTED.sub(" ", text)
    if UNPROVEN_PREDICATE.search(prose):
        return False
    # Numeric-free assertions are not established by a header or words in a
    # question. Accept only explicit verbatim quotations, never an interpretation.
    if not re.search(r"\d", prose):
        return bool(quoted and all(value in literals for value in quoted)
                    and re.fullmatch(r"[\s의에는은는이가을를:·,()]*"
                                     r"(?:(?:값|원본|셀|기록|표시|내용|열|이름|항목)\s*)*"
                                     r"(?:입니다|기록되어 있습니다|표시되어 있습니다)[.!]?", prose))
    return _period_values_match(text, evidence)


def _period_values_match(text, evidence):
    mentions = list(DATE.finditer(text))
    for index, match in enumerate(mentions):
        period = _period(match)
        end = mentions[index + 1].start() if index + 1 < len(mentions) else len(text)
        tail = text[match.end():end]
        # A difference after the final period is computed, not another period
        # value. Bind the first stated raw value following each explicit period.
        raw = next(re.finditer(r"(?<![\d.])\d[\d,]*(?:\.\d+)?", tail), None)
        if raw is None:
            continue
        value = float(raw.group().replace(",", ""))
        candidates = [item for item in evidence if _number(getattr(item, "value", None)) == value]
        if not candidates:
            continue  # Existing numeric verifier handles unsupported numbers.
        matching = [item for item in evidence if _has_period(item, period)]
        if not matching or not any(_related(candidate, source) for candidate in candidates for source in matching):
            return False
    return True


def _has_period(item, asked):
    value = f"{getattr(item, 'value', '')} {getattr(item, 'description', '')}"
    return any(_period(match)[:len(asked)] == asked
               for match in DATE.finditer(value))


def _period(match):
    year, month, day, korean_month, korean_day = match.groups()
    return tuple(int(part) for part in (year, month or korean_month, day or korean_day) if part)


def _related(value, period):
    if value is period:
        return True
    left = re.fullmatch(r"([A-Za-z]+)(\d+)", getattr(value, "reference", "") or "")
    right = re.fullmatch(r"([A-Za-z]+)(\d+)", getattr(period, "reference", "") or "")
    return bool(left and right and value.sheet_name == period.sheet_name
                and left.group(2) == right.group(2))


def _number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _normal(value):
    return re.sub(r"\s+", " ", value).strip().rstrip(".!?").casefold()
