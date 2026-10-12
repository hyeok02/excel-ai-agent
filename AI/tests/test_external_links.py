"""표의 열 이름을 다른 파일 참조로 세지 않는지 검증한다."""
from app.services.external_links import references_other_file


def test_a_table_column_is_not_another_file() -> None:
    """Sales_T[Total]에 경고를 달면 평범한 표에서 행마다 경고가 뜬다."""
    assert not references_other_file("Table1[Amount]")
    assert not references_other_file("=SUM(Sales_T[Total])")
    assert not references_other_file("매출표[금액]")


def test_a_nested_table_reference_is_not_another_file() -> None:
    assert not references_other_file("Sales_T[[#This Row],[Qty]]")


def test_a_real_external_reference_is_still_found() -> None:
    assert references_other_file("[1]Sheet1!A1")
    assert references_other_file("'C:\\폴더\\[Book.xlsx]Sheet1'!A1")
    assert references_other_file("=SUM([2]Data!A:A)")


def test_a_plain_formula_references_no_file() -> None:
    assert not references_other_file("=A1+B2")
    assert not references_other_file("")
