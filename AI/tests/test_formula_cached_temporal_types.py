from datetime import date, datetime

import pytest

from app.agent.query.cell_values import safe_indexed_value
from app.agent.query.formula_resolution import FormulaResolver
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex


def indexed_formula(value, expression="=IFERROR(A1,99)"):
    normalized, kind = safe_indexed_value(value, "=CachedValue()")
    cells = (IndexedCell("Data", "A1", normalized, "=CachedValue()", kind, "yyyy-mm-dd"),
             IndexedCell("Data", "B1", None, expression, "formula", "General"))
    return WorkbookDataIndex("unrelated.xlsx", (IndexedRow("Data", 1, cells),), 2, False)


@pytest.mark.parametrize("value", ["hello", "2026-05-03", "2026-05-03T00:00:00"])
def test_cached_text_with_date_format_remains_text_and_is_not_iferror_fallback(value):
    result = FormulaResolver(indexed_formula(value)).resolve("Data!B1")
    assert result.status == "recovered" and result.value == value


@pytest.mark.parametrize("value, kind", [(date(2026, 5, 3), "formula_date"),
                                         (datetime(2026, 5, 3), "formula_datetime")])
def test_cached_temporal_values_have_explicit_types_and_support_date_parts(value, kind):
    index = indexed_formula(value, "=YEAR(A1)")
    assert index.rows[0].cells[0].value_type == kind
    result = FormulaResolver(index).resolve("Data!B1")
    assert result.status == "recovered" and result.value == 2026


def test_cached_iso_text_is_not_silently_interpreted_as_date():
    result = FormulaResolver(indexed_formula("2026-05-03", "=IFERROR(YEAR(A1),99)")).resolve("Data!B1")
    assert result.status == "unavailable" and result.reason == "unsupported_expression"
