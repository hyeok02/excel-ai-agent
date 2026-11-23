"""Small item tables read by what their columns are: periods, a plan beside its actual, a limit beside a
measurement, or plain columns; and a record list named by its sheet."""
from io import BytesIO

import app.main  # noqa: F401  (the application's import order)
from openpyxl import Workbook

from app.services.insights.facts.context import build_workbook_context
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.workbook_parser import parse_workbook


def _report(rows, title="표"):
    book = Workbook()
    book.active.title = title
    for row in rows:
        book.active.append(row)
    stream = BytesIO()
    book.save(stream)
    context = build_workbook_context(parse_workbook("t.xlsx", stream.getvalue()))
    report = validate_workbook_insights(WorkbookInsightReport(overview="", insights=[], limitations=[]), context)
    return report.overview, [item.fact for item in report.insights]


def test_period_columns_are_read_as_each_items_change():
    overview, facts = _report([["지점별 분기 매출 (단위: 만원)"], [], ["지점", "FY2022", "FY2023", "FY2024"],
                               ["강남", 300, 320, 410], ["홍대", 280, 300, 250], ["잠실", 100, 120, 130]])
    assert overview.startswith("이 파일에는 지점별 분기 매출 자료가 담겨 있습니다.")
    assert facts[0].startswith("강남: FY2022 300에서 FY2024 410으로 110(36.7%) 증가했습니다.")
    assert "최근 구간은 FY2023 320에서 FY2024 410으로 90(28.1%) 증가했습니다(단위: 만원)." in facts[0]


def test_a_plan_beside_its_actual_and_a_limit_beside_a_measurement():
    _, facts = _report([["팀", "목표", "실적", "달성률"], ["영업팀", 100, 120, 1.2], ["마케팅팀", 80, 60, 0.75],
                        ["개발팀", 50, 50, 1]])
    assert facts[0] == ("실적 합계는 목표 230 대비 230으로 목표의 100.0%입니다. "
                        "목표보다 높은 팀은 영업팀, 낮은 팀은 마케팅팀입니다.")
    _, facts = _report([["설비", "항목", "측정값", "기준값"], ["A-1", "진동", 3, 5], ["A-2", "온도", 90, 80],
                        ["A-3", "압력", 10, 20]])
    assert facts[0].startswith("측정값이 기준값을 넘은 설비는 A-2(온도)입니다.")


def test_plain_columns_name_their_largest_and_smallest_items():
    _, facts = _report([["상품", "단가", "재고"], ["볼펜", 500, 120], ["노트", 1500, 80], ["가위", 3500, 12]])
    assert facts[0] == "‘단가’는 가위(3,500)가 가장 높고, 볼펜(500)이 가장 낮습니다."
    assert facts[1] == "‘재고’는 볼펜(120)이 가장 많고, 가위(12)가 가장 적습니다."


def test_a_record_list_is_named_by_its_sheet():
    rows = [["주문번호", "날짜", "수량"]] + [[f"O-{n}", f"2025-01-{n:02d}", 10 + n * 37 % 50] for n in range(1, 13)]
    overview, _ = _report(rows, "주문")
    assert overview.startswith("이 파일은 2025년 1월 1일부터 2025년 1월 12일까지의 ‘주문’ 시트의 기록 12건을")


def test_an_answer_scale_is_read_as_good_and_bad_shares():
    _, facts = _report([["문항", "매우만족", "만족", "보통", "불만", "매우불만"], ["속도", 10, 10, 5, 10, 5],
                        ["가격", 30, 10, 0, 5, 5], ["품질", 5, 5, 10, 20, 10]])
    assert facts[0] == "긍정 응답(매우만족·만족) 비율은 가격이 80.0%로 가장 높고, 품질이 20.0%로 가장 낮습니다."
    assert "부정 응답(불만·매우불만) 비율은 품질이 60.0%로 가장 높습니다." in facts[1]


def test_record_sheets_named_by_month_are_compared_and_english_words_take_their_particles():
    from io import BytesIO
    from app.services.insights.facts.context import build_workbook_context as context_of
    from app.services.insights.narratives.narrative_values import subject_particle
    book = Workbook()
    for index, (month, base) in enumerate((("January", 10), ("February", 20), ("March", 30))):
        sheet = book.active if index == 0 else book.create_sheet()
        sheet.title = month
        sheet.append(["Invoice", "Total", "Rating"])
        for number in range(5):
            sheet.append([f"{month[:3]}-{number}", base + number, 7])
    stream = BytesIO()
    book.save(stream)
    from app.services.insights.narratives.sheet_periods import sheet_period_report
    items, overview = sheet_period_report(context_of(parse_workbook("m.xlsx", stream.getvalue())))
    assert items[0].fact.startswith("Total 합계는 ‘January’ 60, ‘February’ 110, ‘March’ 160입니다.")
    assert overview == "‘January’ 대비 ‘March’ Total 합계는 166.7% 증가했습니다."  # Rating is never added up
    assert [subject_particle(word) for word in ("TV Show", "Billing", "Budget", "Revenue")] == ["가", "이", "이", "가"]
