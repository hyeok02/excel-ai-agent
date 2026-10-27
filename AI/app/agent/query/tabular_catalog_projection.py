"""Bound planning input by relevant source columns, not a fixed left prefix."""
import re

from openpyxl.utils import range_boundaries


def request_ranges(question):
    return [match.group().replace("$", "").upper() for match in re.finditer(
        r"(?<![\w])\$?[A-Za-z]{1,3}\$?[1-9]\d*:\$?[A-Za-z]{1,3}\$?[1-9]\d*(?!\d)", question)]


def range_matches(table, question):
    a, b, c, d = range_boundaries(table.reference)
    ranges = request_ranges(question)
    return bool(ranges) and all(a <= e <= g <= c and b <= f <= h <= d
                               for e, f, g, h in map(range_boundaries, ranges))


def ranked_columns(table, question, tokens):
    """Keep a source identity axis and code/label matches beyond column 80."""
    first = table.columns[0].id

    def relevance(column):
        names = [column.display_header] + [text for _, text in column.source_identifiers]
        exact = sum(len(name) * 4 for name in names if name.casefold() in question.casefold())
        text = " ".join(names + [str(value) for value in column.sample_values]).casefold()
        return exact + sum(len(token) for token in tokens if len(token) > 1 and token in text)

    return sorted(table.columns, key=lambda column: (column.id != first, -relevance(column)))


def source_matches(table, columns, question):
    """Display a few source rows matching literal values, with their coordinates."""
    ids = {column.id for column in columns}
    matches = []
    for row in table.rows:
        if any(value not in (None, "") and re.search(
                r"(?<![A-Za-z0-9_])" + re.escape(str(value)) + r"(?![A-Za-z0-9_])", question, re.I)
               for column, value in row.values.items() if column in ids):
            matches.append({"row_number": row.row_number,
                            "values": {column: value for column, value in row.values.items() if column in ids}})
        if len(matches) >= 3:
            break
    return matches
