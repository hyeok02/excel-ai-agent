import app.agent  # noqa: F401  (import order: the insight package imports the agent package)
from app.services.insights.display.label_translator import collecting, counter, prepare_labels
from app.services.insights.display.source_labels import (caption_measure, narrative_scope, section_label,
                                                        source_caption, source_label, source_unit)
from tests.label_readings import readings


def test_a_label_reads_as_its_workbook_reading_part_by_part_and_unknown_parts_stay():
    with readings({"Residential": "가정용", "U.S. Total": "미국 전체"}):
        assert source_label("Residential · U.S. Total") == "가정용 · 미국 전체"
        assert source_label("Residential · Mystery") == "가정용 · Mystery"
    assert source_label("Residential") == "Residential"  # no reading prepared: the source text
    assert source_label("Sales") == "Sales"  # a role is never read as revenue by the glossary
    assert source_label("이미 한국어") == "이미 한국어"


def test_units_and_captions_read_as_a_whole_with_calendar_wording_in_korean():
    with readings({"Thousand Megawatthours": "천 MWh",
                   "Average Price of Electricity by State, September 2024 and 2023": "주별 평균 전기요금, September 2024 및 2023년"}):
        assert source_unit("Thousand Megawatthours") == "천 MWh"
        assert source_caption("Table 8.2.B. Average Price of Electricity by State, September 2024 and 2023") == (
            "주별 평균 전기요금, 2024년 9월 및 2023년")
    assert source_unit("Units per case") == "Units per case"
    assert source_caption("Table 2.9: Mystery observations in East Laboratory, 2012-2023") == (
        "Mystery observations in East Laboratory, 2012~2023년")
    assert source_caption("ABC7: Population estimates, mid-2002 to mid-2023") == "Population estimates, 2002년 중반~2023년 중반"


def test_a_caption_names_one_measure_before_its_qualifiers_only():
    with readings({"Population estimates": "인구 추정치"}):
        assert caption_measure("ABC7: Population estimates: Summary for Scotland") == ("인구 추정치", "")
        assert caption_measure("Population estimates and births by region") == ("", "")
        assert caption_measure("Population growth rate by region") == ("", "")
    assert caption_measure("Population estimates: Summary") == ("", "")  # unread: nothing to attach
    with readings({"Population estimates": ("인구 추정치", "명")}):
        assert caption_measure("Population estimates: Summary for the UK") == ("인구 추정치", "명")
        assert caption_measure("Population estimates (thousands): Summary") == ("인구 추정치", "")  # not single persons


def test_the_labels_a_report_shows_are_collected_and_read_once_per_workbook():
    class Translator:
        calls = []

        async def translate(self, labels, context=(), measures=()):
            Translator.calls.append(list(labels))
            return {label: (f"<{label}>", "명" if label == "Fuel supply" else "") for label in labels}

    with readings({}):
        prepare_labels("book-1", lambda: source_label("Fuel supply · Total"), Translator())
        prepare_labels("book-1", lambda: source_label("Fuel supply · Total"), Translator())
        assert Translator.calls == [["Fuel supply", "Total"]]
        assert source_label("Fuel supply · Total") == "<Fuel supply> · <Total>"
        assert counter("Fuel supply") == "명" and counter("Total") == ""
    with collecting() as found:
        source_label("Annual Totals")
        caption_measure("Resident population: Summary for Wales")
    assert "Annual Totals" in found and found.measures == {"Resident population"}  # only measures are asked a count


def test_sections_preserve_comparison_basis_and_only_drop_opaque_sheet_names():
    with readings({"Annual Totals": "연간 합계", "Budget": "예산"}):
        assert narrative_scope("Sheet1", "Annual Totals") == "연간 합계"
        assert narrative_scope("Seoul plant", "Budget") == "Seoul plant · 예산"
    assert section_label("Year 2026") == "2026년"


def test_readings_asked_once_are_kept_on_disk_for_the_next_process():
    from app.services.insights.display import label_translator

    class Translator:
        async def translate(self, labels, context=(), measures=()):
            return {label: (f"<{label}>", "") for label in labels}

    class Exhausted:
        async def translate(self, labels, context=(), measures=()):
            raise RuntimeError("quota exhausted")

    with readings({}):
        prepare_labels("book-2", lambda: source_label("Fuel supply"), Translator())
    label_translator._PREPARED.discard("book-2")  # a restarted process
    with readings({}):
        prepare_labels("book-2", lambda: source_label("Fuel supply"), Exhausted())
        assert source_label("Fuel supply") == "<Fuel supply>"
