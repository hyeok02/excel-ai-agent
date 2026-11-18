"""A column's values over the whole source table, not only the rows the summary sampled.

"런던 인구는?" names LONDON, row 260 of a 404-row sheet whose summary holds its first 172 rows.
Reading the question's words among the sampled values alone would find no London at all.
"""
from openpyxl.utils import range_boundaries

from app.agent.query.streaming_tabular_rows import source_row
from app.agent.query.workbook_source import source_for

MAX_SCANNED = 5_000


def column_values(table, column_id, index):
    """Every value of the column, or the sampled ones when the source cannot be read again."""
    sampled = [row.values.get(column_id) for row in table.rows]
    source = source_for(index) if not table.complete else None
    if source is None:
        return sampled
    top = range_boundaries(table.reference)[1]
    values = []
    try:
        with source.scan_rows(table.sheet_name, table.reference) as rows:
            for indexed in rows:
                if indexed.row_number == top or indexed.row_number in table.metadata_rows:
                    continue
                values.append(source_row(indexed, table).values.get(column_id))
                if len(values) > MAX_SCANNED:
                    return sampled
    except Exception:
        return sampled
    return values
