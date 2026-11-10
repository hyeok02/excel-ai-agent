"""Store the recalculated results of formulas that read approved cells.

The edited file asks Excel to recalculate when it opens, but until then every
formula keeps the result saved with the original (TotalPrice 108.46 after its
UnitPrice changed). Anything that reads the file without Excel saw the old total.
Here the workbook's own formula evaluator recalculates every formula. It is
trusted only if it first reproduces every result saved in the original file, and
only formulas that read an approved cell get a new saved result. All of them
must be numbers the evaluator could compute, or nothing is refreshed. The patch
touches nothing but those results, which is checked byte for byte; on any doubt
the file is returned exactly as the approved edit left it.
"""
import math
import re
from dataclasses import replace
from io import BytesIO
from zipfile import ZipFile

from app.agent.query.formula_resolution import FormulaResolver
from app.agent.query.formula_resolution_models import FormulaLimits
from app.agent.query.index import build_workbook_data_index
from app.agent.writeback.models import VerificationCheck
from app.agent.writeback.package_editor import _worksheet_paths
from app.agent.writeback.package_preservation import _without_values
from app.agent.writeback.cached_result_patch import _patched
from app.agent.writeback.package_xml import _xml_elements

LIMITS = FormulaLimits(max_cells=500_000, max_range_cells=200_000, max_formulas=20_000, timeout_seconds=10.0)
MAX_BYTES = 20_000_000
_FORMULA = re.compile(rb"<(?:\w+:)?f[\s>/]")


def refresh_cached_results(filename, original, modified, changes):
    """(content, check): the edited file with refreshed formula results, or unchanged and None."""
    try:
        updates = _recalculated(filename, original, modified, changes)
        if not updates:
            return modified, None
        refreshed = _patched(modified, updates)
        if not _only_results_changed(filename, modified, refreshed, updates):
            return modified, None
    except (ValueError, KeyError, OSError, ArithmeticError, RecursionError):
        return modified, None
    return refreshed, VerificationCheck(
        name="cached_results", passed=True,
        detail=f"승인한 값을 읽는 수식 {len(updates)}개의 저장된 결과값을 새 값으로 다시 계산해 반영")


def _evaluated(filename, content):
    index = build_workbook_data_index(filename, content, max_cells=math.inf, max_rows=math.inf)
    formulas = {cell.reference: cell for row in index.rows for cell in row.cells if cell.formula}
    if index.truncated or not formulas or len(formulas) > LIMITS.max_formulas:
        return None, None
    blank = replace(index, rows=[replace(row, cells=tuple(replace(cell, value=None) if cell.formula else cell
                                                        for cell in row.cells)) for row in index.rows])
    results = FormulaResolver(blank, LIMITS).resolve_all()
    if len(results) != len(formulas) or any(result.status != "recovered" for result in results):
        return None, None
    return formulas, {result.reference: result for result in results}


def _recalculated(filename, original, modified, changes):
    if len(modified) > MAX_BYTES or not _has_formulas(original):
        return {}
    before, check = _evaluated(filename, original)
    # The evaluator must reproduce every result Excel saved before it may write any.
    if before is None or any(not _same(cell.value, check[ref].value) for ref, cell in before.items()):
        return {}
    cells, results = _evaluated(filename, modified)
    if cells is None:
        return {}
    changed = {f"{change.sheet_name}!{change.reference.upper()}" for change in changes}
    updates = {}
    for ref, result in results.items():
        if ref in changed or not changed & set(result.inputs):
            continue
        old, new = cells[ref].value, result.value
        if not _number(new) or not (old is None or _number(old)):
            return {}  # a text or date result is not refreshed alone: nothing is
        if old is None or not _same(old, new):
            updates[ref] = new
    return updates


def _has_formulas(content):
    # A workbook without a single formula has no saved result to refresh: skip reading it again.
    with ZipFile(BytesIO(content)) as package:
        return any(_FORMULA.search(package.read(path)) for path in _worksheet_paths(package).values())


def _only_results_changed(filename, before, after, updates):
    with ZipFile(BytesIO(before)) as old, ZipFile(BytesIO(after)) as new:
        paths = _worksheet_paths(old)
        refs = {}
        for ref in updates:
            sheet, address = ref.rsplit("!", 1)
            refs.setdefault(paths[sheet], set()).add(address.upper())
        if old.namelist() != new.namelist() or any(
                old.read(name) != new.read(name) for name in old.namelist() if name not in refs):
            return False
        for path, addresses in refs.items():
            if (_without_values(old.read(path), addresses) != _without_values(new.read(path), addresses)
                    or _formulas(old.read(path), addresses) != _formulas(new.read(path), addresses)):
                return False
    index = build_workbook_data_index(filename, after, max_cells=math.inf, max_rows=math.inf)
    saved = {cell.reference: cell.value for row in index.rows for cell in row.cells if cell.reference in updates}
    return all(_same(saved.get(ref), value) for ref, value in updates.items())


def _formulas(xml, addresses):
    return {span.attributes.get("r", "").upper(): [xml[child.start:child.end] for child in span.value_children
                                                   if child.name == "f"]
            for span in _xml_elements(xml, addresses) if span.name == "c"}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _same(old, new):
    if _number(old) and _number(new):
        return math.isclose(old, new, rel_tol=1e-9, abs_tol=1e-9)
    return old == new
