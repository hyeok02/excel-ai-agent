"""Small, complete source reads; absence becomes blank only after exhaustion."""
from app.agent.query.index import IndexedCell
from app.agent.query.workbook_source_models import SourceReadError


def read_source_range(source, requested, maximum):
    if requested.area > maximum:
        raise SourceReadError("resource_limit")
    addresses = set(requested.addresses())
    cells = {}
    scan = source.scan_rows(requested.sheet, requested.address)
    with scan as stream:
        for row in stream:
            if row.sheet_name != requested.sheet:
                raise SourceReadError("wrong_source")
            cells.update((cell.address, cell) for cell in row.cells if cell.address in addresses)
    if not scan.complete:
        raise SourceReadError("incomplete_range")
    return [cells.get(address) or IndexedCell(requested.sheet, address, None, None, "blank")
            for address in requested.addresses()]
