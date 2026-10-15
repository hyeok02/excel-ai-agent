"""Source observations cannot stand in for unexecuted conditions or another period."""
import re
from types import SimpleNamespace

from app.agent.query.question_dates import question_date_bounds
from app.agent.query.references import REFERENCE_PATTERN
from app.agent.query.tabular_request_numeric import numeric_constraints_match

FILTER = re.compile(r"아닌|아니라|제외|외의|말고|이외|빼고|!=|≠|\b(?:not|except|excluding|without|or|either)\b|"
                    r"또는|혹은|가장|제일|최대|최소|(?:상위|하위|처음|첫|top|bottom|first)\s*\d+|"
                    r"\d[\d,.]*\s*[가-힣A-Za-z%]*\s*(?:초과|미만|이상|이하)", re.I)
IDENTIFIER = re.compile(r"(?<![A-Za-z0-9가-힣])(?:[A-Za-z가-힣][A-Za-z가-힣0-9]*[-_])+"
                        r"[A-Za-z0-9]+(?![A-Za-z0-9_])|"
                        r"(?<![A-Za-z0-9])(?:[A-Za-z]+\d+[A-Za-z0-9]*|[가-힣]+[A-Z0-9][A-Za-z0-9]*)")
POSSESSIVE = re.compile(r"(?:^|\s|[‘'\"])([^\s‘’'\"?!]+?)의(?=\s|[‘'\"])")
CONTEXT_WORDS = {"그", "이", "둘", "두", "각", "전체", "항목", "원본", "이전", "다음", "값", "표", "파일", "시트"}


def observation_constraints_match(question, evidence, source):
    # Qualified references have already been checked geometrically by claim_scope.
    # Their column addresses are not entity IDs and date-like sheet names are not periods.
    question = REFERENCE_PATTERN.sub(" ", question)
    # Canonical query execution owns filters/ranking and their population. A
    # selected raw cell supplies no proof that these conditions were executed.
    if FILTER.search(question):
        return False
    empty_plan = SimpleNamespace(filters=[], operation="lookup")
    empty_table = SimpleNamespace(columns=[], rows=[])
    if not numeric_constraints_match(question, empty_plan, empty_table):
        return False
    if not _period_matches(question, evidence):
        return False
    subjects = {match.group().casefold() for match in IDENTIFIER.finditer(question)}
    subjects.update(match.group(1).casefold() for match in POSSESSIVE.finditer(question)
                    if match.group(1) not in CONTEXT_WORDS)
    return all(_subject_present(subject, source.casefold()) for subject in subjects)


def _subject_present(subject, source):
    # Dates are checked with calendar precision, not literal spelling.
    if any(question_date_bounds(subject)):
        return True
    return bool(re.search(rf"(?<![A-Za-z0-9_]){re.escape(subject)}(?![A-Za-z0-9_])", source))


def _period_matches(question, evidence):
    lower, upper = question_date_bounds(question)
    if lower is None and upper is None:
        return True
    if lower is not None and upper is not None and lower > upper:
        return False
    found = []
    for item in evidence:
        # Dates must be in a real cell value, not a guessed description. The
        # claim binder already requires period labels to be in the value's row.
        if not isinstance(item.value, str):
            continue
        start, end = question_date_bounds(item.value)
        if start is not None and end is not None and start <= end:
            found.append((start, end))
    return bool(found) and all((lower is None or lower <= start) and (upper is None or end <= upper)
                               for start, end in found)
