from dataclasses import replace

import pytest

from app.agent.query.workbook_source_models import SourceReadError, SourceReadLimits
from tests.test_workbook_source_scan import content, make_source


def consume(source, reference):
    with source.scan_rows("Records", reference) as scan:
        list(scan)
    return scan


@pytest.mark.parametrize("limits", [SourceReadLimits(max_cells=5), SourceReadLimits(max_rows=1)])
def test_rectangle_budget_rejects_before_opening(content, limits):
    source = make_source(content, limits=limits)
    with pytest.raises(SourceReadError, match="resource_limit"):
        source.scan_rows("Records", "A1:C2")
    assert source._budget.reads == 0


@pytest.mark.parametrize("limits", [SourceReadLimits(max_cells=5), SourceReadLimits(max_rows=1)])
def test_cumulative_budget_never_certifies_second_partial_read(content, limits):
    source = make_source(content, limits=limits)
    assert consume(source, "A1:C1").complete
    scan = source.scan_rows("Records", "A2:C2")
    with pytest.raises(SourceReadError, match="resource_limit"):
        with scan:
            list(scan)
    assert not scan.complete and scan._books is None


def test_read_count_and_elapsed_budget_are_request_local(content, monkeypatch):
    source = make_source(content, limits=SourceReadLimits(max_reads=1))
    assert consume(source, "A1").complete
    with pytest.raises(SourceReadError, match="resource_limit"):
        consume(source, "A2")
    assert consume(make_source(content), "A2").complete
    from app.agent.query import workbook_source_models as module
    clock = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: clock[0])
    source = make_source(content, limits=SourceReadLimits(max_seconds=2))
    scan = source.scan_rows("Records", "A1:C3")
    with pytest.raises(SourceReadError, match="time_limit"):
        with scan:
            iterator = iter(scan)
            next(iterator)
            clock[0] = 3.0
            next(iterator)
    assert not scan.complete and scan._books is None


def test_missing_allowed_sheet_cannot_be_proven_empty(content):
    from app.agent.query.workbook_source_models import SourceSheet
    source = replace(make_source(content), sheets=(SourceSheet("Absent", 1, 1),))
    scan = source.scan_rows("Absent", "A1")
    with pytest.raises(SourceReadError, match="missing_sheet"):
        with scan:
            list(scan)
    assert not scan.complete and scan._books is None
