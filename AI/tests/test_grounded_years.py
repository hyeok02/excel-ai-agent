"""A sentence giving values for two years must cite a cell for each year."""
from app.agent.query.grounded_interpretation import _years_cited


def test_two_years_read_from_one_cell_are_not_kept():
    sentence = "현재 천식 유병률은 2010년 5.8%에서 2020년 5.8%로 변화가 없습니다."
    assert not _years_cited(sentence, set(), 1)
    assert not _years_cited(sentence, {2020}, 2)
    assert _years_cited(sentence, {2010, 2020}, 2) and _years_cited(sentence, set(), 2)
    assert _years_cited("2020년 값은 5.8%입니다.", set(), 1)


def test_a_ranking_of_days_does_not_answer_a_month_question():
    from types import SimpleNamespace
    from app.agent.query.calendar_grain import day_groups
    table = SimpleNamespace(rows=[SimpleNamespace(values={"B": "2023-01-04T00:00:00"}),
                                  SimpleNamespace(values={"B": "2023-02-11T00:00:00"})])
    assert day_groups("2023년 판매금액이 가장 높은 달은?", table, "B")
    assert not day_groups("판매금액이 가장 높은 날은?", table, "B")


def test_a_sum_over_period_columns_states_their_total():
    from types import SimpleNamespace
    from app.agent.query.tabular_results import aggregate_text
    columns = [SimpleNamespace(id=letter, header=f"2024 Q{number}", display_header=f"2024 Q{number}")
               for number, letter in enumerate("BCDE", 1)]
    row = SimpleNamespace(values={"B": 1103, "C": 1100, "D": 1369, "E": 1346}, number_formats={}, formulas={})
    text, _ = aggregate_text("numeric_summary", columns, [row], "sum")
    assert "‘2024 Q1’~‘2024 Q4’ 전체: 합계 4,918" in text
