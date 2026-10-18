from io import BytesIO
from zipfile import ZipFile

import pytest

from app.agent.query.workbook_source_models import SourceReadError
from tests.test_workbook_source_scan import content, make_source


def mismatched_cell(content):
    output = BytesIO()
    with ZipFile(BytesIO(content)) as source, ZipFile(output, "w") as target:
        for entry in source.infolist():
            data = source.read(entry.filename)
            if entry.filename == "xl/worksheets/sheet1.xml":
                assert b'r="B5"' in data
                data = data.replace(b'r="B5"', b'r="B500"')
            target.writestr(entry, data)
    return output.getvalue()


def test_malformed_xml_cannot_relabel_out_of_range_cells_as_verified_rows(content):
    scan = make_source(mismatched_cell(content)).scan_rows("Records", "A1:C5")
    with pytest.raises(SourceReadError, match="inconsistent_cell_coordinate"):
        with scan:
            list(scan)
    assert not scan.complete and scan._books is None
