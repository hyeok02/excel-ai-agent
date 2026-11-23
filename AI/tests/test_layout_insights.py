"""Insights read from a file's layout: a two-way column keeping amounts apart, sheets named by
their years, years over their halves, and two tables side by side over the same items."""
from io import BytesIO

import app.main  # noqa: F401  (the application's import order)
from openpyxl import Workbook

from app.services.insights.facts.context import build_workbook_context
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.workbook_parser import parse_workbook


def _report(fill):
    book = Workbook()
    fill(book)
    stream = BytesIO()
    book.save(stream)
    context = build_workbook_context(parse_workbook("t.xlsx", stream.getvalue()))
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[], limitations=[]), context)
    return report.overview, [item.fact for item in report.insights]


def test_amounts_of_a_two_way_column_are_kept_apart():
    def fill(book):
        book.active.title = "장부"
        book.active.append(["날짜", "구분", "분류", "금액"])
        for month in (1, 2, 3):
            book.active.append([f"2024.0{month}.25", "수입", "급여", 1000])
            for kind, value in (("식비", 10 * month), ("교통", 25), ("문화", 5)):
                book.active.append([f"2024.0{month}.0{month}", "지출", kind, value])
    overview, facts = _report(fill)
    assert overview.startswith("이 파일은 ‘구분’ 기록 12건을 정리한 목록입니다. ")  # the first sentence as before
    assert facts[0] == "구분별 금액 합계는 수입 3,000, 지출 150입니다. 지출은 수입의 5.0%입니다."
    assert "분류 3개로 나눠 보면 교통이 75(50.0%)로 가장 크고, 문화가 15(10.0%)로 가장 작습니다" in facts[1]
    assert "2024년 3월(60)이 가장 많고, 2024년 1월(40)이 가장 적습니다" in facts[2]


def test_sheets_of_one_layout_named_by_their_years_are_compared():
    def fill(book):
        for index, (year, values) in enumerate((("2022년", (10, 20, 30)), ("2023년", (15, 20, 10)))):
            sheet = book.active if index == 0 else book.create_sheet()
            sheet.title = year
            sheet.append(["제품", "매출액"])
            for name, value in zip(("A", "B", "C"), values):
                sheet.append([name, value])
    overview, facts = _report(fill)
    assert "매출액 합계는 ‘2022년’ 60에서 ‘2023년’ 45로 15(25.0%) 감소했습니다." in facts
    assert "1개 증가, 1개 감소했고, C가 30에서 10으로 20(66.7%) 감소해 변화 폭이 가장 큽니다." in facts[-1]
    assert overview.endswith("‘2022년’ 대비 ‘2023년’ 매출액 합계는 25.0% 감소했습니다.")


def test_years_over_their_halves_are_added_up_by_year():
    def fill(book):
        sheet = book.active
        sheet.title = "반기"
        sheet.append(["반기 매출 (단위: 백만원)"])
        sheet.append([])
        sheet.append(["제품", "2023", None, "2024", None])
        sheet.append([None, "상반기", "하반기", "상반기", "하반기"])
        for row in (["가", 10, 20, 30, 40], ["나", 50, 50, 10, 10], ["다", 5, 5, 5, 5]):
            sheet.append(row)
        sheet.merge_cells("B3:C3")
        sheet.merge_cells("D3:E3")
    _, facts = _report(fill)
    assert facts[0] == "연도별 합계는 2023년 140에서 2024년 100으로 40(28.6%) 감소했습니다(단위: 백만원)."
    assert "가가 30에서 70으로" in facts[1] and "나가 100에서 20으로" in facts[1]


def test_two_tables_side_by_side_over_the_same_items_are_read_together():
    def fill(book):
        sheet = book.active
        sheet.title = "요약"
        sheet.append(["지점별 인원", None, None, None, "지점별 매출(억원)"])
        sheet.append(["지점", "인원", None, None, "지점", "매출"])
        for name, people, sales in (("서울", 10, 50), ("부산", 5, 40), ("대전", 20, 20)):
            sheet.append([name, people, None, None, name, sales])
    overview, facts = _report(fill)
    assert overview.endswith("인원은 대전, 매출은 서울이 가장 많습니다.")
    assert "1인당 매출은 부산(8)이 가장 높고, 대전(1)이 가장 낮습니다(단위: 억원)." in facts
