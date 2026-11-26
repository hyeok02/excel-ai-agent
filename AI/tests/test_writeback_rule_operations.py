"""Rows picked by rank or average, and values the request describes instead of stating: text, rounding, dates."""
from app.agent.query.tabular_query_models import TabularFilter
from app.agent.writeback.models import AverageFilter, RowRank
from app.agent.writeback.rounding_words import rounding_places
from app.agent.writeback.time_periods import moved_by
from tests.test_writeback_rules import _changes, _propose

COOKIES = [TabularFilter(column_id="Category", operator="equals", value="Cookies")]


def test_rank_and_average_are_computed_from_the_source_rows() -> None:
    rank = {"operation": "set", "amount": 4, "rank": RowRank(column_id="UnitPrice", order="highest")}
    assert _changes(_propose("쿠키 중 단가가 가장 높은 상품의 단가를 4로 바꿔줘", **rank)) == {"C5": 4}
    guessed = _propose("쿠키 중 단가가 가장 높은 상품의 단가를 4로 바꿔줘", operation="set", amount=4,
                       filters=[*COOKIES, TabularFilter(column_id="UnitPrice", operator="equals", value=3.0)])
    assert guessed["status"] == "blocked"  # the model's own guess of the highest row is not taken
    below = {"operation": "set", "amount": 2, "average_filters": [AverageFilter(column_id="UnitPrice", operator="less_than")]}
    assert _changes(_propose("쿠키 중 단가가 평균보다 낮은 상품 단가를 2로 바꿔줘", **below)) == {"C2": 2}


def test_text_rounding_and_another_rows_value() -> None:
    everything = {"filters": []}
    assert _changes(_propose("Bars 상품명 앞에 'NEW-'를 붙여줘", target_column_id="Product", operation="prepend_text",
                             amount="NEW-", filters=[TabularFilter(column_id="Category", operator="equals", value="Bars")])) == {"B3": "NEW-Carrot"}
    assert _changes(_propose("Product의 'Chip'을 'Crisp'으로 바꿔줘", target_column_id="Product", operation="replace_text",
                             find_text="Chip", amount="Crisp", **everything)) == {"B2": "Crisp", "B5": "Crisp"}
    assert _changes(_propose("UnitPrice를 정수로 반올림해줘", operation="round", amount=0, **everything)) == {"C2": 2, "C4": 3}
    assert _propose("UnitPrice를 정리해줘", operation="round", amount=0, **everything)["status"] == "blocked"
    other = [TabularFilter(column_id="Product", operator="equals", value="Carrot")]
    assert _changes(_propose("Oat 단가를 Carrot 단가와 같게 맞춰줘", operation="set", amount=None, value_row_filters=other,
                             filters=[TabularFilter(column_id="Product", operator="equals", value="Oat")])) == {"C4": 2}


def test_places_and_periods_are_read_from_the_request() -> None:
    assert rounding_places("소수 첫째 자리에서 반올림") == {0} and rounding_places("소수 둘째 자리까지 반올림") == {2}
    assert rounding_places("백원 단위로 반올림") == {-2} and rounding_places("십의 자리에서 반올림") == {-2}
    assert rounding_places("천만원 단위로 반올림") == {-7} and rounding_places("Round it to whole numbers") == {0}
    assert moved_by("PRJ-A 마감일을 2주 미뤄줘", 14, "days", 1) and moved_by("한 달씩 연장해줘", 1, "months", 1)
    assert not moved_by("2주 미뤄줘", 2, "months", 1) and not moved_by("마감일을 2주 바꿔줘", 2, "weeks", 1)


def test_a_date_or_number_is_named_as_the_request_writes_it() -> None:
    from app.agent.writeback.rule_mentions import named_value
    assert named_value("2024-11-03T00:00:00", "11월 3일 강남점 매출") and not named_value("2024-11-04T00:00:00", "11월 3일")
    assert named_value(873, "가입자 873명") and not named_value(873, "가입자가 가장 많은 달")


def test_code_ranges_column_units_and_a_text_edit_kept_in_its_named_column() -> None:
    from app.agent.writeback.rule_rows import matching_rows
    from app.agent.writeback.rule_units import unit_note

    class Row:
        def __init__(self, code):
            self.values = {"A": code}
    class Table:
        rows, columns = [Row(f"P0{n:02d}") for n in range(8, 14)], ()
    picked = [TabularFilter(column_id="A", operator="greater_than_or_equal", value="P010"),
              TabularFilter(column_id="A", operator="less_than_or_equal", value="P012")]
    assert [row.values["A"] for row in matching_rows(Table, picked)] == ["P010", "P011", "P012"]
    assert unit_note(["예산(만원)"], 12000, "예산을 1억 2천만원으로") and not unit_note(["예산(만원)"], 1200, "예산을 1억 2천만원으로")
    wrong = _propose("Product에 있는 'Chip'을 'Crisp'으로 바꿔줘", target_column_id="Category", operation="replace_text",
                     find_text="Chip", amount="Crisp", filters=[])
    assert wrong["status"] == "blocked"  # the request names Product; Category is not where the text is


def test_another_columns_value_with_a_calculation_dotted_dates_and_named_weeks() -> None:
    from app.agent.writeback.models import ColumnComparison
    from app.agent.writeback.rule_rows import _date
    from app.agent.writeback.rule_units import scaled_note
    cheaper = [ColumnComparison(column_id="UnitPrice", operator="less_than", other_column_id="Qty")]
    doubled = _propose("쿠키 중 UnitPrice가 Qty보다 낮으면 UnitPrice를 Qty의 2배로 맞춰줘", operation="multiply", amount=2,
                       value_column_id="Qty", column_filters=cheaper)
    assert _changes(doubled) == {"C2": 6, "C4": 10, "C5": 12}
    dropped = _propose("쿠키 중 UnitPrice가 Qty보다 낮으면 UnitPrice를 Qty의 2배로 맞춰줘", operation="set", amount=None,
                       value_column_id="Qty", column_filters=cheaper)
    assert dropped["status"] == "blocked"  # the 2배 left out of the reading
    assert _date("2024.03.02").day == 2 and moved_by("마감일을 일주일 연장해줘", 1, "weeks", 1)
    assert scaled_note(["집행액(만원)"], 11024, 12024, "집행액을 1,000만원씩 늘려줘")
