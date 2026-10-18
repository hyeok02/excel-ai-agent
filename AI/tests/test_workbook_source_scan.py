from dataclasses import replace
from hashlib import sha256
from io import BytesIO

from openpyxl import Workbook
import pytest

from app.agent.query.index import build_workbook_data_index
from app.agent.query.question_index import build_question_data_index
from app.agent.query.workbook_source import WorkbookSource, source_for
from app.agent.query.workbook_source_models import SourceReadError, SourceSheet
from app.services.workbook_parser import parse_workbook


@pytest.fixture
def content():
    book = Workbook()
    sheet = book.active
    sheet.title = "Records"
    sheet.append(["Name", "Amount", "Ratio"])
    sheet.append(["Alpha", 3, 0.25])
    sheet["C2"].number_format = "0.0%"
    sheet.append(["Beta", "=B2+1", None])
    sheet.append([None, None, None])
    sheet.append(["Tail", 9, None])
    hidden = book.create_sheet("Excluded")
    hidden.append(["private", 999])
    hidden.sheet_state = "hidden"
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


def make_source(content, **kwargs):
    return WorkbookSource(sha256(content).hexdigest(), (SourceSheet("Records", 5, 3),),
                          content, **kwargs)


def test_exhaustion_proves_blank_rows_and_preserves_original_cell_types(content):
    source = make_source(content)
    original = source.content
    scan = source.scan_rows("Records", "A2:C5")
    assert not scan.complete
    with scan:
        rows = list(scan)
    assert scan.complete and scan.scanned_rows == 4 and scan.scanned_cells == 12
    assert rows[0].cells[2].value == 0.25
    assert rows[0].cells[2].number_format == "0.0%"
    assert rows[1].cells[1].formula == "=B2+1"
    assert rows[1].cells[1].value is None
    assert rows[2].cells == ()
    assert rows[3].row_number == 5 and rows[3].cells[1].value == 9
    assert source.content is original
    assert sha256(original).hexdigest() == source.source_digest
    assert repr(original) not in repr(source)


def test_partial_iteration_never_claims_complete_and_closes_once(content):
    source = make_source(content)
    scan = source.scan_rows("Records", "A1:C5")
    with scan:
        iterator = iter(scan)
        assert next(iterator).row_number == 1
    assert not scan.complete and scan._books is None
    elapsed = source._budget.seconds
    scan.__exit__()
    assert source._budget.seconds == elapsed
    with pytest.raises(SourceReadError, match="already_consumed"):
        scan.__enter__()


@pytest.mark.parametrize("reference", ["A:A", "1:10", "A0:B2", "B3:A1", "A1:XFE2", "A1:B1048577"])
def test_invalid_rectangles_are_rejected(content, reference):
    with pytest.raises(SourceReadError, match="invalid_range"):
        make_source(content).scan_rows("Records", reference)


def test_excluded_sheet_and_invalid_bytes_fail_closed(content):
    with pytest.raises(SourceReadError, match="excluded_sheet"):
        make_source(content).scan_rows("Excluded", "A1:B1")
    scan = make_source(b"not an excel archive").scan_rows("Records", "A1")
    with pytest.raises(SourceReadError, match="unreadable_source"):
        with scan:
            list(scan)
    assert not scan.complete and scan._books is None


def test_only_question_indexes_attach_source_and_digest_mismatch_disables_it(content):
    summary = parse_workbook("fixture.xlsx", content)
    plain = build_workbook_data_index("fixture.xlsx", content, {"Records"})
    index = build_question_data_index("fixture.xlsx", content, summary)
    assert source_for(plain) is None
    assert source_for(index).authorized_sheets == frozenset({"Records"})
    assert source_for(replace(index, source_digest="wrong-workbook")) is None


def test_disjoint_tail_reads_do_not_change_prefix_coverage(content, monkeypatch):
    from app.agent.query import index as index_module
    monkeypatch.setattr(index_module, "MAX_INDEXED_CELLS", 4)
    summary = parse_workbook("fixture.xlsx", content)
    index = build_question_data_index("fixture.xlsx", content, summary)
    original_rows = index.rows
    assert index.truncated_for({"Records"})
    for reference in ("A1:C1", "A5:C5"):
        with source_for(index).scan_rows("Records", reference) as scan:
            list(scan)
        assert scan.complete
    assert index.rows is original_rows
    assert index.indexed_cell_count == 4
    assert index.truncated_for({"Records"})
