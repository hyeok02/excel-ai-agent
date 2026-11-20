"""Table plans whose result cannot be what was asked are left to the calculation over the whole table."""
from datetime import date
from types import SimpleNamespace as N

from app.agent.query.tabular_misread import misread


def _plan(operation="row_list", order_by=None, limit=None, group_by=()):
    return N(operation=operation, order_by=order_by, limit=limit, group_by=list(group_by))


def _rows(*values):
    return [N(values=value) for value in values]


def test_one_row_summarized_column_by_column_is_a_misread():
    table = N(columns=[N(id="A", header="지표"), N(id="B", header="1월"), N(id="C", header="2월")])
    row = _rows({"A": "전환율", "B": 0.1, "C": 0.2})
    assert misread("전환율 평균은?", _plan("numeric_summary"), table, row, row, ["B", "C"])
    assert misread("1월 전환율 평균은?", _plan("numeric_summary"), table, row, row, ["B"]) is None


def test_a_top_row_shown_by_shared_values_is_a_misread_and_a_named_one_is_not():
    table = N(columns=[N(id="A", header="일자"), N(id="B", header="품목"), N(id="C", header="출고")])
    rows = _rows({"A": date(2024, 10, 1), "B": "가", "C": 70}, {"A": date(2024, 10, 1), "B": "나", "C": 9},
                 {"A": date(2024, 10, 2), "B": "가", "C": 50})
    top = _plan(order_by="C", limit=1)
    assert misread("출고가 가장 많았던 날은?", top, table, rows, rows[:1], ["A", "C"])
    assert misread("출고가 가장 많았던 건은?", top, table, rows, rows[:1], ["A", "B", "C"]) is None


def test_a_part_of_the_year_read_from_no_month_is_a_misread():
    table = N(columns=[N(id="A", header="지역"), *(N(id=f"M{n}", header=f"{n}월") for n in range(1, 13)),
                       N(id="T", header="합계")])
    row = _rows({"A": "인천", "T": 1449})
    assert misread("인천 4분기 합계는?", _plan("lookup"), table, row, row, ["T"])
    assert misread("인천 연간 합계는?", _plan("lookup"), table, row, row, ["T"]) is None
    assert misread("인천 4분기 합계는?", _plan("numeric_summary"), table, row, row, ["M10"]) is None


def test_an_average_written_out_keeps_its_cells_format():
    from app.agent.query.gpt_calc_cells import result_style
    used = [("S!B2", N(number_format="0.0%")), ("S!C2", N(number_format="0.0%"))]
    assert result_style("([S!B2]+[S!C2])/2", used) == "0.0%"
    assert result_style("[S!B2]/[S!C2]*100", used) is None


def test_a_day_grouped_by_reads_without_its_midnight_time():
    from datetime import datetime
    from app.agent.query.gpt_calc_tables import _label
    assert [_label(datetime(2024, 10, 21)), _label("2024-10-21T00:00:00"), _label(datetime(2024, 10, 21, 9, 30)),
            _label(None)] == ["2024-10-21", "2024-10-21", "2024-10-21 09:30:00", "빈칸"]


def test_an_outline_label_named_once_over_its_rows_is_not_a_misread():
    table = N(columns=[N(id="A", header="Sector"), N(id="B", header="2024")])
    rows = _rows({"A": "Transport", "B": 110.4}, {"A": None, "B": 70}, {"A": None, "B": 40})
    assert misread("가장 많은 부문은?", _plan(order_by="B", limit=1), table, rows, rows[:1], ["A", "B"]) is None
