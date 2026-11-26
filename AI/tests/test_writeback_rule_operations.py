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
