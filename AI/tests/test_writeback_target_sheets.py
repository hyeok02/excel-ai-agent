import pytest

from tests.support.writeback_target_fixtures import proposal


@pytest.mark.parametrize("instruction,drafts", [
    ("'Sales One'!$b$2를 12로 수정", [("Other", "B2", 12)]),
    ("'Sales One'!$b$2를 12로 수정", [("Sales One", "B3", 12)]),
    ("Missing!B2를 12로 수정", [("Sales One", "B2", 12)]),
    ("'Missing'!B2를 12로 수정", [("Sales One", "B2", 12)]),
    ("Missing 시트의 B2를 12로 수정", [("Sales One", "B2", 12)]),
    ("B2를 12로 수정", [("Sales One", "B2", 12)]),
    ("Sales One Notebook January 값을 12로 수정", [("Sales One", "B3", 12)]),
    ("Sales One Notebook January 값을 12로 수정", [("Sales One", "C2", 12)]),
    ("Sales One Notebook January 값을 12로 수정", [("Other", "B2", 12)]),
    ("Sales One B2 말고 C2를 12로 수정", [("Sales One", "B2", 12)]),
    ("Sales One B2에서 C2로 복사해줘", [("Sales One", "B2", 10)]),
    ("Sales One B2 값을 C2에 12로 수정", [("Sales One", "B2", 12)]),
])
def test_rejects_wrong_sheet_ambiguous_address_and_same_valued_wrong_labels(instruction, drafts):
    body = proposal(instruction, drafts)
    assert body["status"] == "blocked", body
    assert not body["changes"]


@pytest.mark.parametrize("instruction,drafts", [
    ("'Sales One'!$b$2를 12로 수정", [("Sales One", "B2", 12)]),
    ("Sales One!B2를 12로 수정", [("Sales One", "B2", 12)]),
    ("Sales One 시트의 B2를 12로 수정", [("Sales One", "B2", 12)]),
    ("'O''Brien'!B2를 12로 수정", [("O'Brien", "B2", 12)]),
    ("Sales One Notebook January 값을 12로 수정", [("Sales One", "B2", 12)]),
    ("Sales One B2 말고 C2를 12로 수정", [("Sales One", "C2", 12)]),
    ("Sales One B2와 Other B2를 12로 수정", [("Sales One", "B2", 12), ("Other", "B2", 12)]),
    ("Sales One B2는 12로, Other B2는 15로 수정", [("Sales One", "B2", 12), ("Other", "B2", 15)]),
    ("Sales One B2와 C3를 12로 수정", [("Sales One", "B2", 12), ("Sales One", "C3", 12)]),
])
def test_allows_qualified_multiple_sheet_and_disjoint_destinations(instruction, drafts):
    body = proposal(instruction, drafts)
    assert body["status"] == "ready", body
    assert len(body["changes"]) == len(drafts)
    assert body["risks"] == []
