"""A share of some rows in all rows, asked as a ratio without another column."""
from tests.test_gpt_calc_fallback import _ask, _table


def test_a_share_of_the_filtered_rows_is_their_part_of_all_rows():
    east = _ask({"kind": "table", "method": "East의 Amount 비중", "cells": None,
                 "table": _table(filters=[{"column": "Region", "op": "eq", "value": "East"}], aggregate="ratio")})
    assert "비율: 58.82% (Amount 200 / 전체 340)" in east.answer
    rows = _ask({"kind": "table", "method": "East 행 비율", "cells": None,
                 "table": _table(filters=[{"column": "Region", "op": "eq", "value": "East"}], measure=None,
                                 aggregate="ratio")})
    assert "비율: 50.00% (행 수 3 / 전체 6)" in rows.answer
