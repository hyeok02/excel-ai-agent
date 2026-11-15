"""A header of consecutive years nothing labels as years is read so, and the reading is stated."""
import asyncio
from io import BytesIO

from openpyxl import Workbook

from app.services.insights.facts.horizontal_series import extract_horizontal_series
from app.services.insights.generator import LangChainInsightGenerator, SOURCE_FALLBACK_NOTICE
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report
from app.services.insights.narratives.record_display import build_record_insight
from app.services.workbook_parser import parse_workbook
from tests.test_horizontal_series import cell, region


def _table(header, *rows):
    columns = "ABCDEFG"
    return region([cell(f"{column}1", value) for column, value in zip(columns, header)],
                  *([cell(f"{column}{number}", value) for column, value in zip(columns, row)]
                    for number, row in enumerate(rows, start=2)))


def _report(source):
    series = extract_horizontal_series([source])
    return series, horizontal_trend_report({"sheets": [{"name": "Data", "business_facts": {"horizontal_series": series}}]})


def test_consecutive_year_header_is_read_as_years_and_says_so():
    series, (items, overview) = _report(_table(["Region", 2019, 2020, 2021, 2022], ["East", 10, 12, 11, 15]))
    assert series and series[0]["axis_inferred"] is True
    assert "2019년 10에서 2022년 15로" in items[0].fact
    assert "해석: 머리글 2019~2022를 연도로 읽어 계산했습니다." in items[0].fact
    assert "해석: 머리글 2019~2022를 연도로" in overview


def test_headers_naming_codes_and_thin_or_uneven_headers_stay_unread():
    for header in ("Product", "SKU", "Product ID", "상품코드", "Model"):
        assert extract_horizontal_series([_table([header, 2018, 2019, 2020], ["Units sold", 12, 8, 9])]) == []
    assert extract_horizontal_series([_table(["Metric", 2021, 2022], ["Revenue", 10, 12])]) == []
    assert extract_horizontal_series([_table(["Metric", 2019, 2021, 2022], ["Revenue", 10, 12, 11])]) == []


def test_years_the_source_labels_are_not_called_an_interpretation():
    titled = region([cell("A1", "Revenue by region, 2019-2022")],
                    [cell("A2", "Region"), *[cell(f"{c}2", y) for c, y in zip("BCDE", range(2019, 2023))]],
                    [cell("A3", "East"), *[cell(f"{c}3", v) for c, v in zip("BCDE", (10, 12, 11, 15))]])
    series, (items, _) = _report(titled)
    assert "axis_inferred" not in series[0] and "해석:" not in items[0].fact


def test_unread_header_numbers_are_names_and_repeated_numbers_all_count():
    header = [{"cell": f"{c}1", "label": None, "value": v} for c, v in zip("ABCD", ("Product", 2018, 2019, 2020))]
    assert build_record_insight("Data", header).fact == "확인된 내용은 ‘Product’ · ‘2018’ · ‘2019’ · ‘2020’입니다."
    row = [{"cell": f"{c}3", "label": None, "value": v} for c, v in zip("ABCDE", ("West", 5, 6, 7, 6))]
    assert build_record_insight("Data", row).fact == "확인된 내용은 ‘West’ · ‘5’ · ‘6’ · ‘7’ · ‘6’입니다."


class FailingModel:
    async def ainvoke(self, _messages):
        raise RuntimeError("model unavailable")


def test_a_failed_model_call_quotes_source_cells_instead_of_failing(monkeypatch):
    book = Workbook()
    for row in (["Product", 2018, 2019, 2020], ["Units sold", 12, 8, 9]):
        book.active.append(row)
    stream = BytesIO()
    book.save(stream)
    generator = LangChainInsightGenerator("unused", 10, "minimal")
    monkeypatch.setattr(generator, "_build_model", lambda _profile: FailingModel())
    report = asyncio.run(generator.generate(parse_workbook("codes.xlsx", stream.getvalue())))
    assert report.insights and report._generation_notice == SOURCE_FALLBACK_NOTICE


def test_inferred_years_do_not_become_question_answer_evidence():
    from app.agent.query.verified_calculation_context import fact_calculations
    series = extract_horizontal_series([_table(["Region", 2019, 2020, 2021], ["East", 10, 12, 11])])
    calculations, _ = fact_calculations({"sheets": [{"name": "Data", "business_facts": {"horizontal_series": series}}]})
    assert series and calculations == []
