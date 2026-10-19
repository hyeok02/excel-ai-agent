"""Synthetic source populations for period-first trend validation."""
from dataclasses import replace

from tests.tabular_query_fixtures import table_fixture

QUESTION = "2024년 전체 직원 수의 기간별 추이를 설명해줘"
VALID_ROWS = [["2024-01-31", 100], ["2024-02-29", 150], ["2024-03-31", 120]]


def series(rows, layout="vertical", *, sheet="Arbitrary"):
    matrix = ([["Date", "Total Employees"], *rows] if layout == "vertical" else
              [["Metric", *[row[0] for row in rows]],
               ["Total Employees", *[row[1] for row in rows]]])
    summary, index = table_fixture([(1, 1, matrix)], sheet_name=sheet)
    normalize_formulas(summary)
    return summary, index


def normalize_formulas(summary):
    for region in summary.sheets[0].regions:
        for row in region.analysis_rows:
            for cell in row:
                value = cell.get("value")
                if isinstance(value, str) and value.startswith("="):
                    cell.update(formula=value, value=None, cached_value=None)


def formats(summary, index, changes):
    for region in summary.sheets[0].regions:
        for row in region.analysis_rows:
            for cell in row:
                if cell["address"] in changes:
                    cell["number_format"] = changes[cell["address"]]
    rows = tuple(replace(row, cells=tuple(
        replace(cell, number_format=changes.get(cell.address, cell.number_format))
        for cell in row.cells)) for row in index.rows)
    return replace(index, rows=rows)


def answered(answer):
    assert answer is not None, "Expected source-bound trend result"
    assert answer.status in {"answered", "limited"}, answer.model_dump()


def period_checked(answer):
    answered(answer)
    assert answer.status == "answered" and answer.verification.level == "request_checked", answer.model_dump()
    assert "3개 관측값" in answer.answer
    assert "2023-12-31" not in answer.answer and "2025-01-31" not in answer.answer
    assert "100명 → 120명" in answer.answer


def refused(answer):
    assert answer is not None, "Supported trend wording must not fall through to a generator"
    assert answer.status == "insufficient_evidence", answer.model_dump()
    assert answer.verification.level == "unverified", answer.model_dump()
