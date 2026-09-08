import re
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook

from app.services.insights.facts.context import build_workbook_context
from app.services.insights.quality import build_source_report
from app.services.insights.verification.reference_matching import matching_references
from app.services.insights.verification.validation_index import extract_references
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.workbook_parser import parse_workbook


def _school_context():
    """Sparse, transposed date columns; nutrient rows are beyond an initial preview."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "식단"
    values = {
        "C3": "학교 급식 영양 표시", "C5": "일자",
        "H5": datetime(2026, 9, 1), "J5": datetime(2026, 9, 2),
        "C6": "중식", "H6": "현미밥, 미역국, 배추김치(9)",
        "J6": "보리밥, 된장국(5)",
        "C20": "열량(kcal)", "H20": 720, "J20": 740,
        "C21": "단백질(g)", "H21": 25, "J21": 27,
    }
    for address, value in values.items():
        sheet[address] = value
    sheet["H5"].number_format = sheet["J5"].number_format = "yyyy-mm-dd"
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    summary = parse_workbook("synthetic-school-menu.xlsx", stream.getvalue())
    return build_workbook_context(summary)


def _result():
    context = _school_context()
    return validate_workbook_insights(build_source_report(context), context)


def _covers(insight, address):
    citations = set().union(*(extract_references(item) for item in insight.evidence))
    return any(matching_references(citation, {f"식단!{address}".casefold()})
               for citation in citations)


def _mentions_day(text, day):
    return re.search(rf"2026(?:-|년\s*)0?9(?:-|월\s*)0?{day}(?:일)?", text) is not None


def test_school_nutrient_narrative_retains_sparse_rows_and_their_units():
    result = _result()
    energy = [item for item in result.insights if "열량" in item.fact]
    protein = [item for item in result.insights if "단백질" in item.fact]

    assert energy and protein
    energy_text = " ".join(item.fact for item in energy)
    protein_text = " ".join(item.fact for item in protein)
    assert "720" in energy_text and "740" in energy_text and "kcal" in energy_text
    assert re.search(r"(?<!\d)25(?!\d)", protein_text)
    assert re.search(r"(?<!\d)27(?!\d)", protein_text)
    assert "g" in protein_text
    assert all(any(_covers(item, address) for item in energy) for address in ("C20", "H20", "J20"))
    assert all(any(_covers(item, address) for item in protein) for address in ("C21", "H21", "J21"))


def test_school_menu_summary_preserves_dates_without_borrowing_another_domain():
    result = _result()
    menu = [item for item in result.insights if "현미밥" in item.fact or "보리밥" in item.fact]
    facts = " ".join(item.fact for item in result.insights)

    assert menu
    assert "현미밥" in facts and "보리밥" in facts
    assert _mentions_day(facts, 1) and _mentions_day(facts, 2)
    assert any(_covers(item, "H5") and _covers(item, "H6") for item in menu)
    assert any(_covers(item, "J5") and _covers(item, "J6") for item in menu)
    for forbidden in ("Riot", "직원", "구조조정", "매출", "6,101", "5,417"):
        assert forbidden not in result.model_dump_json()
    assert result.validation.model_dump().get("overview_validated") is True
