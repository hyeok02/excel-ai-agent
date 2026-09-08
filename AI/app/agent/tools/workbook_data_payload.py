from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import HeaderContext, header_for


def row_payload(row: IndexedRow, headers: HeaderContext) -> dict[str, object]:
    return {
        "sheet_name": row.sheet_name,
        "row_number": row.row_number,
        "cells": [
            {
                "reference": cell.reference,
                "header": header_for(headers, row.sheet_name, row.row_number, cell.address),
                "value": cell.value,
                "formula": cell.formula,
                "number_format": cell.number_format,
            }
            for cell in row.cells
        ],
    }
