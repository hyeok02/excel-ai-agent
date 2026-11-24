"""Insights over report layouts: months heading amount and change columns, measures in units over plans,
a budget the same every month, a large list read again from its file, and formulas saved without results."""
from io import BytesIO

import app.main  # noqa: F401  (the application's import order)
from openpyxl import Workbook

from app.services.insights.facts.context import build_workbook_context
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.narratives.large_tables import reading
from app.services.insights.narratives.narrative_values import topic_particle
from app.services.insights.verification.formula_values import unsaved_formula_notice
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.workbook_details.sample_caps import wider_samples
from app.services.workbook_parser import parse_workbook


def _report(fill, wide=False):
    book = Workbook()
    fill(book)
    stream = BytesIO()
    book.save(stream)
    content = stream.getvalue()
    with wider_samples(wide):
        summary = parse_workbook("t.xlsx", content)
    with reading(content):
        context = build_workbook_context(summary)
        report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[], limitations=[]), context)
    return report.overview, [item.fact for item in report.insights], summary


def test_months_over_cost_and_change_columns_are_read_from_the_cost_and_added_up():
    def fill(book):
        sheet = book.active
        sheet.title = "Cost variations"
        sheet.append(["Usage type", "Monthly cost", None, None, None, None, "Total"])
        sheet.append([None, "2017-10", "2017-11", None, "2017-12", None, None])
        sheet.append([None, "Cost", "Variation", "Cost", "Variation", "Cost", None])
        for number in range(24):
            sheet.append([f"Usage-{number}", 10 + number, 0.1, 12 + number, -0.2, 8 + number, 30 + 3 * number])
        sheet.merge_cells("C2:D2")
        sheet.merge_cells("E2:F2")
    overview, facts, _ = _report(fill)
    assert "전체 합계: 2017년 10월 516에서 2017년 12월 468로 48(9.30%) 감소했습니다." in facts[0]
    assert overview.startswith("이 파일은 ‘Cost variations’ 시트에 Usage type 24개의 2017-10~2017-12 값을")


def test_measures_in_units_are_compared_across_plans_never_with_each_other():
    def fill(book):
        book.active.title = "계획"
        book.active.append([None, None, "계획A", "계획B", "계획C"])
        for name, unit, values in (("매출", "원", (320, 480, 640)), ("판매수", "개", (400, 600, 800)),
                                   ("직원수", "명", (2, 3, 5))):
            book.active.append([name, unit, *values])
    _, facts, _ = _report(fill)
    assert facts[0] == "‘매출’은 계획C(640원)가 가장 많고, 계획A(320원)가 가장 적습니다."


def test_a_budget_the_same_every_month_is_told_by_what_a_month_is_made_of():
    def fill(book):
        book.active.title = "Budget"
        book.active.append(["Item", "January", "February", "March", "Total"])
        for name, value in (("Rent", 1500), ("Food", 250), ("Gas", 50), ("Phone", 85)):
            book.active.append([name, value, value, value, value * 3])
    overview, facts, _ = _report(fill)
    assert facts[0] == "January~March 값이 매달 같고, January 기준 큰 항목은 Rent 1,500, Food 250, Phone 85입니다."
    assert topic_particle("FY21") == "은" and topic_particle("FY22") == "는"


def test_a_list_larger_than_the_sample_is_totalled_from_the_whole_file():
    from app.services.workbook_details import analysis_samples

    def fill(book):
        book.active.title = "Sales"
        book.active.append(["Fiscal_Year", "Product_Category", "Revenue", *(f"c{n}" for n in range(9))])
        for number in range(1500):
            book.active.append(["FY20" if number % 2 else "FY21", ("TV", "Phone", "Laptop")[number % 3], 10,
                                *(number for _ in range(9))])
    cap = analysis_samples.INSIGHT_SHEET_CELLS
    analysis_samples.INSIGHT_SHEET_CELLS = 4_000  # a sample far smaller than the list
    try:
        _, facts, _ = _report(fill, wide=True)
    finally:
        analysis_samples.INSIGHT_SHEET_CELLS = cap
    assert "Fiscal_Year별 Revenue 합계는 FY20 7,500, FY21 7,500입니다(전체 1,500건)." in facts
    assert "Product_Category별 Revenue 합계는 TV 5,000, Phone 5,000, Laptop 5,000입니다(전체 1,500건)." in facts


def test_formulas_saved_without_their_results_are_told():
    def fill(book):
        book.active.append(["a", "b", "sum"])
        for number in range(1, 7):
            book.active.append([number, number, f"=A{number + 1}+B{number + 1}"])
    *_, summary = _report(fill)
    assert unsaved_formula_notice(summary).startswith("수식 6개의 계산 결과가 파일에 저장되어 있지 않아")
