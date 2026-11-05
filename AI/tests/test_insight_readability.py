"""Cards read line by line, name the series' extremes and quote the table's own source notes."""
from io import BytesIO

from openpyxl import Workbook

from app.services.analysis_strategy import AnalysisDepth, select_analysis_profile
from app.services.insights.facts.context import build_workbook_context
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.narratives.series_path import series_shape
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.workbook_parser import parse_workbook

YEARS = list(range(2015, 2025))
ATTACKS = [0.055, 0.058, 0.054, 0.05, 0.047, 0.03, 0.026, 0.031, 0.033, 0.036]
CURRENT = [0.087, 0.096, 0.09, 0.085, 0.08, 0.058, 0.061, 0.064, 0.067, 0.065]


def _report(notes=True, quoted=True):
    book = Workbook()
    sheet = book.active
    sheet.append(["Indicator H1. Percentage of children ages 0 to 17 years with asthma, 2015-2024"])
    sheet.append(["Measure", *YEARS])
    sheet.append(["Asthma Attack Prevalence", *ATTACKS])
    sheet.append(["Current Asthma Prevalence", *CURRENT])
    for row in (3, 4):
        for column in range(2, 12):
            sheet.cell(row, column).number_format = "0.0%"
    if notes:
        sheet.append(["DATA: National Health Interview Survey."])
        sheet.append(["NOTES:"])
        name = '"Asthma attack prevalence"' if quoted else "Asthma attack prevalence"
        sheet.append([f"*{name} represents children who reported an asthma attack during the past 12 months."])
    stream = BytesIO()
    book.save(stream)
    summary = parse_workbook("asthma.xlsx", stream.getvalue())
    context = build_workbook_context(summary, select_analysis_profile(summary, AnalysisDepth.AUTO))
    return validate_workbook_insights(WorkbookInsightReport(overview="", insights=[]), context)


def test_cards_put_each_reading_on_its_own_line_and_name_real_extremes() -> None:
    report = _report()
    attack = next(item for item in report.insights if "발작" in item.title or "Attack" in item.topic)
    lines = attack.fact.split("\n")
    assert lines[0].endswith("감소했습니다.") and lines[1].startswith("최근 구간은 ")
    assert "가장 높았던 시점은 2016년 5.8%" in attack.fact and "가장 낮았던 시점은 2021년 2.6%" in attack.fact
    assert "주요 시점" not in attack.fact and "증가와 감소가 반복" not in attack.fact


def test_the_tables_own_source_and_quoted_definition_are_shown() -> None:
    report = _report()
    assert "(출처: National Health Interview Survey.)" in report.overview
    attack = next(item for item in report.insights if "Attack" in item.topic)
    current = next(item for item in report.insights if "Current" in item.topic)
    assert '원본 정의: "Asthma attack prevalence" represents children' in attack.fact
    assert "원본 정의" not in current.fact  # The note defines another measure.
    assert all(item.validation_status == "verified" for item in report.insights)


def test_a_note_that_does_not_quote_the_measure_defines_nothing() -> None:
    assert all("원본 정의" not in item.fact for item in _report(quoted=False).insights)
    report = _report(notes=False)
    assert "출처" not in report.overview and all("원본 정의" not in item.fact for item in report.insights)


def test_series_shape_lists_short_paths_and_names_inner_extremes_of_long_ones() -> None:
    assert series_shape(["a", "b", "c"], [3, 1, 2], ["3", "1", "2"]) == "기간별 기록은 a 3 → b 1 → c 2입니다. 감소한 뒤 반등했습니다."
    assert series_shape(list("abcde"), [1, 2, 3, 4, 5], list("12345")) == "증가세가 이어졌습니다."
    assert series_shape(list("abcde"), [5, 9, 1, 4, 3], list("59143")) == "가장 높았던 시점은 b 9, 가장 낮았던 시점은 c 1입니다."
    assert series_shape(list("abcde"), [9, 2, 6, 3, 1], list("92631")) == ""  # both extremes are the ends
