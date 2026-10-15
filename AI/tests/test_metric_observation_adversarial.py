"""Independent adversarial cases: source values alone do not verify the request."""
from types import SimpleNamespace

from openpyxl.utils import get_column_letter

from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.metric_scalar_answers import metric_scalar_answer


def _index(sheets, number_format="$#,##0"):
    rows = []
    for sheet, matrix in sheets.items():
        for number, values in enumerate(matrix, 1):
            cells = tuple(IndexedCell(sheet, f"{get_column_letter(column)}{number}", value, None,
                                      "number" if isinstance(value, (int, float)) else "text",
                                      number_format if isinstance(value, (int, float)) else "General")
                          for column, value in enumerate(values, 1) if value is not None)
            if cells:
                rows.append(IndexedRow(sheet, number, cells))
    return WorkbookDataIndex("arbitrary.xlsx", tuple(rows), sum(len(row.cells) for row in rows), False)


def _report(entity, years, revenue, debt=None):
    rows = [[entity], [None, "Annual actual"], ["Period", *[f"{year}-12-31" for year in years]],
            ["Revenue", *revenue]]
    if debt is not None:
        rows.append(["Total Debt", *debt])
    return rows


def _checked(answer):
    return answer is not None and answer.verification is not None and answer.verification.level == "request_checked"


def test_latest_entity_cannot_borrow_a_newer_value_from_another_company_sheet():
    index = _index({"One": _report("Alpha Company", [2024, 2025], [100, 110]),
                    "Two": _report("Beta Company", [2025, 2026], [200, 220])})
    answer = metric_observation_answer("Alpha Company의 최신 매출은?", None, index)
    assert not _checked(answer) or ("110" in answer.answer and "220" not in answer.answer)


def test_named_entity_with_missing_requested_period_cannot_use_another_entity():
    index = _index({"One": _report("Alpha Company", [2023, 2024], [100, 110]),
                    "Two": _report("Beta Company", [2024, 2025], [200, 220])})
    answer = metric_observation_answer("Alpha Company의 2025년 매출은?", None, index)
    assert not _checked(answer)


def test_two_requested_metrics_cannot_be_certified_as_one_longest_label():
    index = _index({"Report": _report("Alpha Company", [2024, 2025], [100, 110], [12, 14])})
    answer = metric_observation_answer("2025년 Revenue와 Total Debt를 각각 알려줘", None, index)
    assert not _checked(answer) or ("Revenue" in answer.answer and "Total Debt" in answer.answer)


def test_two_requested_undated_metrics_cannot_be_certified_as_one_longest_label():
    index = _index({"Report": [["Revenue", 110], ["Total Debt", 14]]})
    answer = metric_scalar_answer("Revenue와 Total Debt를 각각 알려줘", None, index)
    assert not _checked(answer) or ("Revenue" in answer.answer and "Total Debt" in answer.answer)


def test_currency_number_format_does_not_erase_magnitude_in_source_caption():
    index = _index({"Report": [["Amounts in USD millions"], [None, "Annual actual"],
                               ["Period", "2024-12-31", "2025-12-31"], ["Revenue", 100, 110]]})
    answer = metric_observation_answer("2025년 Revenue는 얼마야?", None, index)
    assert not _checked(answer) or "백만" in answer.answer


def test_latest_excludes_future_estimate_suffix_on_year_header():
    index = _index({"Report": [["Company revenue"], ["Period", "2025A", "2026E"],
                               ["Revenue", 100, 150]]})
    answer = metric_observation_answer("최신 Revenue는 얼마야?", None, index)
    assert not _checked(answer) or ("100" in answer.answer and "150" not in answer.answer)


def test_multi_attribute_intent_cannot_be_certified_by_scalar_period_handler():
    index = _index({"Report": _report("Alpha Company", [2024, 2025], [100, 110])})
    intent = SimpleNamespace(whole_workbook=False, kind="summary")
    answer = metric_observation_answer("2025년 매출과 고객 수를 알려줘", None, index, intent)
    assert not _checked(answer)


def test_scalar_same_named_entity_elsewhere_does_not_authorize_unrelated_metric():
    index = _index({"One": [["Alpha Company"], ["Assets", 100]],
                    "Two": [["Beta Company"], ["Revenue", 220]]})
    answer = metric_scalar_answer("Alpha Company의 Revenue는 얼마야?", None, index)
    assert not _checked(answer)
