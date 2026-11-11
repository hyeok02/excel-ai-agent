"""Series laid out across columns or down rows state a change in one shape."""
from app.services.insights.facts.series_scalars import unit
from app.services.insights.narratives.change_sentence import change_fact, change_sentence
from app.services.insights.narratives.narrative_values import joining_particle, subject_particle
from app.services.insights.narratives.vertical_latest_narratives import vertical_latest_report
from tests.support.recent_record_fixtures import cell, context


def test_whole_period_comes_first_then_the_latest_step():
    whole = change_sentence("1997년 5.5%", "2024년 3.6%", 5.46, 3.64, "%")
    recent = change_sentence("2023년 3.3%", "2024년 3.6%", 3.3, 3.64, "%")
    assert change_fact("천식 발작 경험 비율", whole, recent) == (
        "천식 발작 경험 비율: 1997년 5.5%에서 2024년 3.6%로 1.9%p 감소했습니다.\n"
        "최근 구간은 2023년 3.3%에서 2024년 3.6%로 0.3%p 증가했습니다.")


def test_the_change_is_written_in_the_scale_and_digits_the_reader_sees():
    assert "417.4 백만 톤(" in change_sentence("1990년 790.8 백만 톤", "2024년 373.4 백만 톤", 790.84, 373.42, " 백만 톤")
    assert "0.3억(22.50%)" in change_sentence("2016년 1.2억", "2025년 1.5억", 123456789, 151234567)
    assert "3K(25.83%)" in change_sentence("2016년 12K", "2025년 15K", 12000, 15100)
    assert change_sentence("2023년 5.5%", "2024년 5.5%", 5.46, 5.54, "%").startswith("2023년 5.5%와 2024년 5.5%로")


def test_particles_follow_how_numbers_and_percent_are_read():
    assert [subject_particle(text) for text in ("93,177", "10", "5", "42", "3.6%")] == ["이", "이", "가", "가", "가"]
    assert joining_particle("5.5%") == "와" and joining_particle("2023년 6") == "과"


def test_a_scale_the_format_writes_is_not_named_twice_and_its_currency_stays():
    assert unit({"number_format": '#,##0.0,,"M"'}) == "백만"
    assert unit({"number_format": '$#,##0.0,,"M"'}) == "백만 USD"
    assert unit({"number_format": '#,##0,"K"'}) == "천"


def test_rows_down_the_sheet_read_like_columns_across_it():
    rows = [[cell("A1", "Year"), cell("B1", "Occupancy rate")],
            *([cell(f"A{n}", year), cell(f"B{n}", rate, "0.0%")]
              for n, year, rate in ((2, 2021, .5), (3, 2022, .6), (4, 2023, .9), (5, 2024, .8)))]
    items, overview = vertical_latest_report(context(rows))
    assert items[0].fact.startswith("Data의 점유율: 2021년 50.0%에서 2024년 80.0%로 30%p 증가했습니다.\n"
                                    "최근 구간은 2023년 90.0%에서 2024년 80.0%로 10%p 감소했습니다.\n")
    assert "최근 구간은 2023년 90.0%에서 2024년 80.0%로 10%p 감소했습니다." in overview


def test_a_sheet_named_like_its_metric_is_not_repeated_in_the_subject():
    rows = [[cell("A1", "Year"), cell("B1", "Occupancy rate")],
            *([cell(f"A{n}", year), cell(f"B{n}", rate)] for n, year, rate in ((2, 2022, 5), (3, 2023, 6), (4, 2024, 7)))]
    items, _ = vertical_latest_report(context(rows, name="Occupancy rate"))
    assert items[0].fact.startswith("점유율: 2022년 5에서 2024년 7로")
