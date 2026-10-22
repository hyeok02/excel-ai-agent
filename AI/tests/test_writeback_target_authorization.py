import pytest

from tests.test_writeback_current_value_guard import propose


@pytest.mark.parametrize("instruction,reference,value", [
    ("매출현황 B2를 12로 수정해줘", "B3", 12),
    ("매출현황 $b$2를 12로 수정해줘", "C2", 12),
    ("매출현황 B2:C2를 12로 수정해줘", "B3", 12),
    ("매출현황 B2부터 C2까지 12로 수정해줘", "B3", 12),
    ("매출현황 B2를 =SUM(C2:D2)로 변경해줘", "C2", "=SUM(C2:D2)"),
    ("매출현황 B2 값을 참고해 B3를 12로 변경해줘", "B2", 12),
    ("매출현황 B2는 12로, B3는 15로 수정해줘", "B2", 15),
    ("매출현황 B2는 12로, B3는 15로 수정해줘", "B3", 12),
    ("매출현황 B2는 비우고 B3는 12로 수정해줘", "B3", None),
    ("매출현황 노트북 1월 값을 12로 수정해줘", "B3", 12),
    ("매출현황 노트북 1월 값을 12로 수정해줘", "C2", 12),
    ("매출현황 1월 값을 12로 수정해줘", "B3", 12),
    ("매출현황 B2는 12로 변경, C2의 13은 참고만 해", "B2", 13),
    ("매출현황 B3를 10에서 12로 수정해줘", "B3", 10),
    ("매출현황 B2를 -12로 수정해줘", "B2", 12),
    ("매출현황 B2를 12로 수정해줘", "B2", -12),
    ("매출현황 B2를 -1만으로 수정해줘", "B2", 10000),
    ("매출현황 B2를 1만으로 수정해줘", "B2", 1),
    ("매출현황 B2를 $-12로 수정해줘", "B2", 12),
    ("매출현황 B2를 -$12로 수정해줘", "B2", 12),
])
def test_rejects_wrong_target_or_another_targets_operation(instruction, reference, value):
    response = propose(reference, value, instruction)
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["changes"] == []
    assert response.json()["risks"]


@pytest.mark.parametrize("instruction,reference,value", [
    ("매출현황 B2를 12로 수정해줘", "B2", 12),
    ("매출현황 $b$2를 12로 수정해줘", "B2", 12),
    ("매출현황 B2 : C2를 12로 수정해줘", "B2:C2", 12),
    ("매출현황 B2부터 C2까지 12로 수정해줘", "B2:C2", 12),
    ("매출현황 B2를 =SUM(C2:D2)로 변경해줘", "B2", "=SUM(C2:D2)"),
    ("매출현황 B2 값을 참고해 B3를 12로 변경해줘", "B3", 12),
    ("매출현황 B2는 12로, B3는 15로 수정해줘", "B2", 12),
    ("매출현황 B2는 12로, B3는 15로 수정해줘", "B3", 15),
    ("매출현황 B2와 C2를 12로 수정해줘", "B2", 12),
    ("매출현황 B2와 C2를 12로 수정해줘", "C2", 12),
    ("매출현황 노트북 1월 값을 12로 수정해줘", "B2", 12),
    ("매출현황 모니터 2월 값을 12로 수정해줘", "C3", 12),
    ("매출현황 B2는 10% 줄이고 B3는 15로 수정해줘", "B2", 9),
    ("매출현황 B2를 'C2'로 변경해줘", "B2", "C2"),
    ('매출현황 B2를 "C2"로 변경해줘', "B2", "C2"),
    ("매출현황 B2가 아니라 B3을 12로 변경해줘", "B3", 12),
    ("매출현황 B2를 -12로 수정해줘", "B2", -12),
    ("매출현황 B2를 1만으로 수정해줘", "B2", 10000),
    ("매출현황 B2를 -1만으로 수정해줘", "B2", -10000),
    ("매출현황 B2를 $12로 수정해줘", "B2", 12),
    ("매출현황 B2를 $-12로 수정해줘", "B2", -12),
    ("매출현황 B2를 -$12로 수정해줘", "B2", -12),
])
def test_preserves_valid_explicit_and_natural_requests(instruction, reference, value):
    response = propose(reference, value, instruction)
    assert response.status_code == 200
    assert response.json()["status"] == "ready", response.json()
    assert response.json()["changes"]


def test_partial_explicit_request_is_not_silently_complete():
    body = propose("B2", 12, "매출현황 B2와 C2를 12로 수정해줘").json()
    assert body["status"] == "ready"
    assert any("확인하지 못한 셀" in risk and "C2" in risk for risk in body["risks"])
    assert body["limitations"]
