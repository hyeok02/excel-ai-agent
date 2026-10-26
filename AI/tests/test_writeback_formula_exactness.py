import pytest

from tests.test_writeback_current_value_guard import propose


@pytest.mark.parametrize("instruction,formula,ready", [
    ("매출현황 D2를 =SUM(B2:C2)+9로 변경", "=SUM(B2:C2)", False),
    ("매출현황 D2를 =SUM(B2:C2)+9로 변경", "=SUM(B2:C2)+9", True),
    ("매출현황 D2를 =SUM(B2:C2)*2로 변경", "=SUM(B2:C2)", False),
    ("매출현황 D2를 =SUM(B2:C2)*2로 변경", "=SUM(B2:C2)*2", True),
    ("매출현황 D2를 =B2+C2로 변경", "=B2", False),
    ("매출현황 D2를 =B2+C2로 변경", "=B2+C2", True),
    ('매출현황 D2를 =IF(B2>0,"양수","음수")로 변경', '=IF(B2>0,"양수","음수")', True),
    ('매출현황 D2를 "=SUM(B2:C2)+9"로 변경', '=SUM(B2:C2)+9', True),
    ("매출현황 D2를 '=SUM(B2:C2)+9'로 변경", '=SUM(B2:C2)+9', True),
    ("매출현황 D2를 `=SUM(B2:C2)+9`로 변경", '=SUM(B2:C2)+9', True),
])
def test_only_the_complete_requested_formula_can_be_proposed(instruction, formula, ready):
    body = propose("D2", formula, instruction).json()
    assert (body["status"] == "ready") == ready, body
