"""Two named members compared on one measure, from every source row."""
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.member_comparison_answers import member_comparison_answer
from tests.tabular_query_fixtures import table_fixture

SALES = [["ID", "City", "TotalPrice"], ["ID1", "Boston", 10.5], ["ID2", "LA", 4.0], ["ID3", "Boston", 2.0], ["ID4", "NY", 7.0]]
CROSS = [["Groups", "Wales", "Scotland"], ["Code", "W1", "S1"], ["All Persons", 31, 55], ["Males", 15, 27]]


def _ask(rows, targets, kind="comparison"):
    summary, index = table_fixture([(1, 1, rows)], sheet_name="Data")
    return member_comparison_answer("비교해줘", summary, index, QuestionIntent(False, kind, targets, True))


def test_members_of_a_column_are_totalled_over_every_row_and_compared():
    answer = _ask(SALES, ("Boston", "LA", "TotalPrice"))
    assert answer.answer == "‘City’별 ‘TotalPrice’ 합계: Boston 12.50, LA 4.\nBoston 쪽이 LA보다 8.50 많습니다."
    assert answer.status == "limited" and {item.reference for item in answer.evidence} >= {"B2", "C2", "B4", "C4"}


def test_members_named_as_columns_are_read_on_the_one_total_row():
    assert _ask(CROSS, ("Wales", "Scotland")).answer == "‘All Persons’ 행: Wales 31, Scotland 55.\nScotland 쪽이 Wales보다 24 많습니다."


def test_no_measure_another_kind_or_an_unknown_name_leaves_it_alone():
    assert _ask(SALES, ("Boston", "LA")) is None
    assert _ask(SALES, ("Boston", "LA", "TotalPrice"), kind="aggregation") is None
    assert _ask(SALES, ("Boston", "Paris", "TotalPrice")) is None
