"""Match source identities exactly, allowing only a terminal legal suffix omission."""
import re

from app.agent.query.ambiguity_labels import _source_matches, source_or_reading_mentioned

_ENTITY = re.compile(r"\b(?:owner|holder|company|entity|issuer|organization|customer|vendor|supplier|name)\b|"
                     r"회사|기업|보유자|주주|거래처|고객|이름|명칭", re.I)
_LEGAL = re.compile(r"(?:[\s,]+(?:incorporated|inc|corporation|corp|limited|ltd|llc|plc|company|co)\.?)+$", re.I)


def record_identities(table, question):
    return {str(value) for row in table.rows for column in table.columns
            if column.id not in table.hidden_columns and isinstance(value := row.values.get(column.id), str)
            and 3 <= len(value.strip()) <= 100 and record_mentioned(column.header, value, question)}


def requested_record_rows(table, question, rows):
    matched = [row for row in rows if any(
        column.id not in table.hidden_columns and _ENTITY.search(column.header)
        and isinstance(value := row.values.get(column.id), str)
        and record_mentioned(column.header, value, question) for column in table.columns)]
    return matched or rows


def record_mentioned(header, value, question):
    if source_or_reading_mentioned(value, question):
        return _positive(value, question)
    if not _ENTITY.search(header):
        return False
    shortened = _LEGAL.sub("", value.strip()).strip()
    if shortened == value.strip() or len(re.sub(r"\W", "", shortened)) < 3:
        return False
    # Do not match arbitrary abbreviations or company-name prefixes.
    return _positive(shortened, question)


def _positive(value, question):
    matches = _source_matches(value, question)
    if not matches and source_or_reading_mentioned(value, question):
        return True  # Existing glossary reading, not a newly invented alias.
    return any(not re.search(r"\b(?:not|except|excluding|without)\s*$", question[:match.start()], re.I)
               and not re.match(r"\s*(?:아닌|제외|말고|빼고)", question[match.end():]) for match in matches)
