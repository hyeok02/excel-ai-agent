from app.agent.query.comparison_scope import (
    column_from_address,
    column_number,
    header_references,
    normalized_label,
)
from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_headers import HeaderContext, header_for


def metric_changes(
    rows: list[IndexedRow],
    start_row: IndexedRow,
    end_row: IndexedRow,
    data_start_row: int,
    date_column: str,
    headers: HeaderContext,
    allowed: dict[str, tuple[str, ...]] | None,
) -> list[dict[str, object]]:
    end_cells = {column_from_address(cell.address): cell for cell in end_row.cells}
    metrics = []
    for start in start_row.cells:
        column = column_from_address(start.address)
        end = end_cells.get(column)
        header = header_for(
            headers, start_row.sheet_name, start_row.row_number, start.address
        )
        if (
            column_number(column) <= column_number(date_column)
            or allowed is not None and column not in allowed
            or not header
            or not _allowed_header(header, column, allowed)
            or not _number(start)
            or end is None
            or not _number(end)
        ):
            continue
        references = header_references(
            rows,
            start_row.sheet_name,
            data_start_row,
            column,
            allowed.get(column, (header,)) if allowed else (header,),
        )
        metrics.append(
            {
                "header": header,
                "start_value": start.value,
                "end_value": end.value,
                "change": round(float(end.value) - float(start.value), 10),
                **({"header_references": references} if references else {}),
                "start_reference": start.reference,
                "end_reference": end.reference,
            }
        )
    return metrics


def _allowed_header(
    header: str, column: str, allowed: dict[str, tuple[str, ...]] | None
) -> bool:
    return allowed is None or normalized_label(header) in {
        normalized_label(label) for label in allowed[column]
    }


def _number(cell: IndexedCell) -> bool:
    return isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool)
