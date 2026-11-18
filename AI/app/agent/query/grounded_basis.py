"""Source labels and displayed values for the figures an interpreted answer cites."""
import re
from dataclasses import replace

from app.agent.query.excel_number_formats import display_value, parse_number_format, scaled_value
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.references import normalize_reference

CELL = re.compile(r"([A-Z]+)([1-9]\d*)", re.I)
MAX_BASIS = 16


def source_cells(references, index):
    """The fact's own cells read from the workbook, when the search evidence holds none of them."""
    if index is None:
        return []
    wanted = {normalize_reference(reference) for reference in references if isinstance(reference, str) and ":" not in reference}
    return [_evidence(cell) for row in index.rows for cell in row.cells
            if normalize_reference(cell.reference) in wanted][:MAX_BASIS]


def row_label(cell, available):
    """The leftmost text cell of the value's own row: the record or category it belongs to."""
    column, row = CELL.fullmatch(cell.reference.replace("$", "")).groups()
    same = [item for item in available.values() if item.sheet_name == cell.sheet_name and names(item.value)
            and (found := CELL.fullmatch(item.reference.replace("$", ""))) and found.group(2) == row
            and _order(found.group(1)) < _order(column)]
    return min(same, key=lambda item: _order(CELL.fullmatch(item.reference.replace("$", "")).group(1)), default=None)


def column_header(cell, claim, bound, available):
    """The header cell above the value, in its own column, when the draft or the tool names one.

    The nearest text cell above is used: over 'East' a pivot holds its field name 'Region', and
    the one right above the values names the column itself.
    """
    column, row = CELL.fullmatch(cell.reference.replace("$", "")).groups()
    named = [available.get(normalize_reference(reference))
             for reference in (claim.property_reference if claim else None, bound) if reference]
    above = []
    for item in [*named, *(other for other in available.values() if isinstance(other.value, str))]:
        found = CELL.fullmatch(item.reference.replace("$", "")) if item is not None else None
        if (found and item.sheet_name == cell.sheet_name and found.group(1).upper() == column.upper()
                and int(found.group(2)) < int(row) and names(item.value)):
            above.append((int(found.group(2)), item))
    return max(above, key=lambda entry: entry[0])[1] if named and above else None


def period_numbers(label):
    """The year and month a period label names ("August 2026" is 2026년 8월), as a sentence writes them."""
    from decimal import Decimal
    from app.services.insights.facts.fact_trends import date_value
    when = date_value(label.value)
    return {Decimal(when.year), Decimal(when.month)} if when else set()


def _order(column):
    return len(column), column.upper()


def names(value):
    """Text, or a year: what a row is called rather than what it measures."""
    return isinstance(value, str) and bool(value.strip()) or year(value)


def year(value):
    return number(value) and float(value).is_integer() and 1900 <= value <= 2200


def shown(cell):
    if not number(cell.value):
        return " ".join(str(cell.value).split())
    if year(cell.value) and "," not in str(cell.number_format or ""):
        return str(int(cell.value))  # 2024, not 2,024
    spec = parse_number_format(cell.number_format)
    scaled = scaled_value(cell.value, spec)
    if spec.divisor == 1 and round(scaled, spec.maximum_decimals) != round(scaled, 6):
        spec = replace(spec, minimum_decimals=2, maximum_decimals=2)  # a format hiding decimals the draft may quote
    return display_value(cell.value, spec)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def change_within_one_series(sentence, cells, available):
    """A sentence stating a rise or fall over cited cells needs them to be one series over periods.

    "판매수량이 33에서 44로 증가" read from two sales records is no trend: the cells share a column
    but their rows are two transactions. One row across columns, or one column whose rows are
    named by a period, is a series; a quoted verified fact is checked by its own computation.
    """
    from app.agent.query.answer_clauses import clauses, stated_direction
    from app.services.insights.facts.fact_trends import date_value
    if not any(stated_direction(clause) for clause in clauses(sentence)):
        return True
    stated = [cell for cell in cells if not year(cell.value) and states_value(sentence, cell)]  # a year names a period
    if len(stated) < 2:
        return True
    rows, columns = {}, {}
    for cell in stated:
        column, row = CELL.fullmatch(cell.reference.replace("$", "")).groups()
        rows.setdefault((cell.sheet_name, row), []).append(cell)
        label = row_label(cell, available)
        if label is not None and (year(label.value) or date_value(label.value)):
            columns.setdefault((cell.sheet_name, column.upper()), []).append(cell)
    # At least two of the stated values must be one series; none are when each is its own record.
    return any(len(group) >= 2 for group in (*rows.values(), *columns.values()))


def names_its_records(sentence, cells, available):
    """A value read from one record ("ID07351") is that record's, not its city's or category's.

    A sentence stating such a value without naming the record ("Boston의 판매금액은 58.41") would
    present one sale as a total, so it is not kept; a period, category or pivot label is no record.
    """
    for cell in cells:
        label = row_label(cell, available) if number(cell.value) and not year(cell.value) else None
        if (label is not None and isinstance(label.value, str) and _record_id(label.value)
                and states_value(sentence, cell) and label.value.strip().casefold() not in sentence.casefold()):
            return False
    return True


def _record_id(text):
    """A code naming one record: no spaces, and mostly digits ("ID07351", "100275", "E92000001")."""
    from app.services.insights.display.display_quality import is_identifier_label
    text = text.strip()
    digits = sum(character.isdigit() for character in text)
    if re.fullmatch(r"(?:19|20|21)\d{2}", text):
        return False  # a year names a period
    return bool(text) and " " not in text and (is_identifier_label(text) or digits >= 3 and digits * 2 >= len(text))


def states_value(text, cell):
    """The text writes the cell's number, at its own rounding ("124.2" states 124.19116...)."""
    from decimal import Decimal
    from app.services.insights.verification.numeric_validation import unmatched_numbers
    if not number(cell.value):
        return False
    return unmatched_numbers(text, {abs(Decimal(str(cell.value)))}) != unmatched_numbers(text, set())
