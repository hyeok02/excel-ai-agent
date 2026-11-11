from io import BytesIO

from openpyxl import Workbook

from app.services.insights.facts.context import build_workbook_context
from app.services.insights.narratives.source_narratives import source_narrative_report
from app.services.workbook_parser import parse_workbook


def test_category_share_narrative_names_denominator_and_category():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([
        "Percentage of days with good, moderate, or unhealthy air quality for "
        "children ages 0 to 17 years, 1999-2023"
    ])
    sheet.append(["Year", "Good", "Moderate", "Unhealthy"])
    sheet.append([2022, 0.4302, 0.3069, 0.0296])
    sheet.append([2023, 0.4042, 0.3270, 0.0361])
    for row in sheet.iter_rows(min_row=3, min_col=2, max_row=4, max_col=4):
        for cell in row:
            cell.number_format = "0.00%"
    stream = BytesIO()
    workbook.save(stream)

    summary = parse_workbook("category-share.xlsx", stream.getvalue())
    report = source_narrative_report(build_workbook_context(summary))

    assert (
        "1년 전체 날짜 중 각 공기질 등급에 해당하는 날의 비율 "
        "(0~17세 아동, 1999~2023년)"
    ) in report.overview
    assert "대기질별 일수 비율" not in report.overview
    assert "· 공기질이 '좋음'인 날의 비율: " in report.overview
    assert report.insights[0].title == "공기질이 '좋음'인 날의 비율 변화 · 1999~2023년"
