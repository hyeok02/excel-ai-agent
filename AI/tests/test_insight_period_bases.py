"""A level at a point in time is compared at period end, and sheets in different won units in one unit."""
from tests.test_insight_report_layouts import _report


def _stock(book):
    sheet = book.active
    sheet.title = "재고"
    sheet.append(["제품별 기말 재고 (단위: 개)"])
    sheet.append([])
    sheet.append(["제품", "2023", None, "2024", None])
    sheet.append([None, "상반기", "하반기", "상반기", "하반기"])
    for name, *values in [("A", 30, 25, 20, 15), ("B", 20, 30, 15, 25), ("C", 15, 20, 10, 15)]:
        sheet.append([name, *values])


def _units(book):
    for year, unit, values in [("2023년", "원", (60000, 30000, 20000)), ("2024년", "만원", (6, 3, 2))]:
        sheet = book.active if year == "2023년" else book.create_sheet()
        sheet.title = year
        sheet.append([f"제품별 매출 (단위: {unit})"])
        sheet.append(["제품", "매출"])
        for name, value in zip("ABC", values):
            sheet.append([name, value])


def test_closing_stock_is_compared_at_year_end_not_added_over_halves() -> None:
    overview, facts, _ = _report(_stock)
    assert any("2023년 75에서 2024년 55로" in fact for fact in facts), facts
    assert not any("140" in fact for fact in facts) and "140" not in overview


def test_sheets_in_won_and_man_won_are_compared_in_one_unit() -> None:
    overview, facts, _ = _report(_units)
    assert any("110,000에서 ‘2024년’ 110,000으로 변동이 없었습니다" in fact for fact in facts), facts
    assert "100.0%" not in overview and not any("100.0%" in fact for fact in facts)


def test_the_latest_part_is_found_by_its_name_and_count_units_are_put_in_one_unit() -> None:
    def reversed_halves(book):
        sheet = book.active
        sheet.title = "재고"
        sheet.append(["제품별 기말 재고 (단위: 개)"])
        sheet.append([])
        sheet.append(["제품", "2023", None, "2024", None])
        sheet.append([None, "하반기", "상반기", "하반기", "상반기"])
        for name, *values in [("A", 25, 30, 15, 20), ("B", 30, 20, 25, 15), ("C", 20, 15, 15, 10)]:
            sheet.append([name, *values])

    def counts(book):
        for year, unit, values in [("2023년", "개", (60000, 30000, 20000)), ("2024년", "만개", (6, 3, 2))]:
            sheet = book.active if year == "2023년" else book.create_sheet()
            sheet.title = year
            sheet.append([f"제품별 판매량 (단위: {unit})"])
            sheet.append(["제품", "판매량"])
            for name, value in zip("ABC", values):
                sheet.append([name, value])
    _, facts, _ = _report(reversed_halves)
    assert any("2023년 75에서 2024년 55로" in fact for fact in facts), facts  # 하반기, though its column comes first
    overview, facts, _ = _report(counts)
    assert "100.0%" not in overview and any("변동이 없었습니다" in fact for fact in facts), facts
