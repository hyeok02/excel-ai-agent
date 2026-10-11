"""한 셀을 고치면 무엇이 따라 바뀌는지, 시트를 넘어서도 찾는지 검증한다."""
from app.agent.writeback.formula_ranges import covers, plain_ranges, sheet_ranges
from app.agent.writeback.references import _formula_references


def _references(formula, formula_sheet, target_sheet, target):
    return _formula_references(formula, formula_sheet, target_sheet, target)


def test_finds_a_range_that_names_another_sheet() -> None:
    """승인 화면이 '영향 없음'이라 적어 두고 합계가 조용히 바뀌던 자리다."""
    assert _references("=SUM(Data!B2:B20)", "Summary", "Data", "B5")
    assert not _references("=SUM(Data!B2:B20)", "Summary", "Data", "B99")


def test_reads_a_quoted_sheet_name() -> None:
    assert _references("=SUM('My Sheet'!B2:B9)", "Summary", "My Sheet", "B3")


def test_finds_whole_column_and_whole_row_ranges() -> None:
    assert _references("=SUM(A:A)", "Data", "Data", "A7")
    assert _references("=SUM(5:5)", "Data", "Data", "C5")
    assert _references("=AVERAGE(Data!B:B)", "Summary", "Data", "B9")


def test_leaves_other_sheets_alone() -> None:
    assert not _references("=SUM(Other!B2:B20)", "Data", "Data", "B5")
    assert not _references("=Other!B5", "Data", "Data", "B5")


def test_keeps_finding_what_it_already_found() -> None:
    assert _references("=Data!B5", "Summary", "Data", "B5")
    assert _references("=SUM(B2:B20)", "Data", "Data", "B5")
    assert _references("=B5*2", "Data", "Data", "B5")
    assert not _references("=SUM(B2:B4)", "Data", "Data", "B5")


def test_separates_ranges_that_name_a_sheet_from_the_ones_that_do_not() -> None:
    formula = "=SUM(Data!B2:B20)+SUM(A1:A3)"

    assert sheet_ranges(formula) == [("Data", "B2:B20")]
    assert plain_ranges(formula) == ["A1:A3"]


def test_an_open_ended_range_covers_the_whole_column() -> None:
    assert covers("A:A", 1, 999_999)
    assert covers("5:5", 3, 5)
    assert not covers("B2:B20", 2, 99)
