"""Record lists keyed by a Korean code or name, and score columns, get insights beyond value ranges."""
from io import BytesIO

from openpyxl import Workbook

import app.main  # noqa: F401  (the app's import order)
from app.services.insights.facts.context import build_workbook_context
from app.services.insights.narratives.source_narratives import source_narrative_report
from app.services.workbook_parser import parse_workbook


def _report(header, rows):
    book = Workbook()
    sheet = book.active
    sheet.title = "목록"
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    book.save(stream)
    return source_narrative_report(build_workbook_context(parse_workbook("목록.xlsx", stream.getvalue())))


def test_a_coded_stock_list_states_totals_and_the_largest_category():
    rows = [[f"P{number:03d}", f"품목{number}", "전자" if number % 3 else "사무", number * 10] for number in range(1, 13)]
    report = _report(["품목코드", "품목명", "카테고리", "재고수량"], rows)
    assert "재고수량 합계는 780" in report.overview
    assert "카테고리별로 보면 ‘전자’의 재고수량 합계가" in report.overview


def test_scores_are_read_by_their_mean():
    rows = [[f"R{number:03d}", number % 5 + 1, number % 11] for number in range(1, 11)]
    report = _report(["응답번호", "만족도", "추천점수"], rows)
    assert any("평균은 3이고, 범위는 1~5" in item.fact for item in report.insights)


def test_daily_records_per_category_are_totalled_by_month_and_named_rows_by_name():
    rows = [[f"2024-0{month}-{day:02d}", channel, 150 + month * 10 + day] for month in (7, 8)
            for day in range(1, 7) for channel in ("검색", "SNS")]
    report = _report(["날짜", "채널", "방문자수"], rows)
    assert any(item.fact.startswith("월별 방문자수 합계는 2024년 7월 ") for item in report.insights)
    named = _report(["부서", "예산"], [["영업팀", 700], ["인사팀", 1500], ["재무팀", 600], ["합계", 2800]])
    assert "인사팀 1,500" in named.overview and "2,800" not in named.overview  # the total row is not a member
