from tests.support.writeback_target_fixtures import proposal
from tests.test_writeback_semantic_scope import source


def test_unique_header_rename_keeps_working_without_a_cell_address():
    body = proposal("Orders Revenue 열 이름을 'Net Revenue'로 수정",
                    [("Orders", "C1", "Net Revenue")], source())
    assert body["status"] == "ready", body


def test_repeated_headers_need_an_explicit_target_for_renaming():
    content = source([["Product", "Revenue"], ["Notebook", 10], [],
                      ["Product", "Revenue"], ["Monitor", 20]])
    body = proposal("Orders Revenue 열 이름을 'Net Revenue'로 수정",
                    [("Orders", "B1", "Net Revenue")], content)
    assert body["status"] == "blocked", body


def test_latin_natural_single_metric_request():
    content = source([["Product", "Amount"], ["Notebook", 10]])
    body = proposal("set Orders Amount to 99", [("Orders", "B2", 99)], content)
    assert body["status"] == "ready", body


def test_known_selector_cannot_hide_a_nonexistent_second_selector():
    content = source([["Region", "Product", "Amount"], ["서울", "노트북", 10]])
    missing = proposal("Orders 서울 태블릿 Amount를 99로 수정", [("Orders", "C2", 99)], content)
    assert missing["status"] == "blocked", missing
    valid = proposal("Orders 서울 노트북 Amount를 99로 수정", [("Orders", "C2", 99)], content)
    assert valid["status"] == "ready", valid


def test_dimension_header_qualifies_the_row_not_an_extra_change_column():
    content = source([["부서", "인원"], ["서비스", 1081], ["영업", 50]])
    wrong = proposal("Orders 서비스 부서 인원을 99로 수정", [("Orders", "A2", 99)], content)
    assert wrong["status"] == "blocked", wrong
    correct = proposal("Orders 서비스 부서 인원을 99로 수정", [("Orders", "B2", 99)], content)
    assert correct["status"] == "ready", correct
    percent = proposal("Orders 서비스 부서 인원을 10% 줄여줘", [("Orders", "B2", 973)], content)
    assert percent["status"] == "ready", percent
