from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.query.row_search import search_rows
from app.agent.query.search_terms import relevance, search_terms


def test_finance_aliases_retrieve_separated_comparison_blocks() -> None:
    rows = tuple(
        [
            _row("Analysis", 49, "Transaction Value | TEV / EBITDA Multiple"),
            *[_row("Analysis", number, "filler") for number in range(50, 58)],
            _row("Analysis", 66, "Comparable Median 9.99x"),
            _row("Analysis", 70, "MTGE 5.09x"),
        ]
    )

    result = search_rows(
        rows, "MTGE 거래 EBITDA 배수와 비교군 중앙값을 비교해줘", 6
    )

    assert {49, 66, 70} <= {row.row_number for row in result}
    assert {"latest", "announcement"} <= set(search_terms("최근 이벤트"))


def test_ownership_aliases_return_header_and_rank_one() -> None:
    rows = (
        _row("Ownership", 1, "junk"),
        _row("Ownership", 105, "Owner Name | Percent Held | Rank"),
        _row("Ownership", 106, "1 | The Vanguard Group | 9.44%"),
    )

    result = search_rows(rows, "지분율 최대 주주는 누구야?", 2)

    assert [row.row_number for row in result] == [105, 106]


def test_round_robin_returns_each_anchor_before_context() -> None:
    rows = (
        _row("First", 10, "alpha"),
        _row("First", 11, "context"),
        _row("First", 12, "context"),
        _row("First", 100, "beta"),
        _row("First", 101, "context"),
        _row("Second", 200, "gamma"),
    )

    result = search_rows(rows, "alpha beta gamma", 3)

    assert {(row.sheet_name, row.row_number) for row in result} == {
        ("First", 10), ("First", 100), ("Second", 200),
    }


def test_sparse_rows_use_excel_row_distance() -> None:
    rows = (
        _row("Deals", 7, "near before"),
        _row("Deals", 10, "alpha"),
        _row("Deals", 18, "near after"),
        _row("Deals", 19, "outside window"),
        _row("Deals", 500, "distant"),
    )

    result = search_rows(rows, "alpha", 10)
    row_numbers = {row.row_number for row in result}

    assert {7, 10, 18} <= row_numbers
    assert not {19, 500} & row_numbers


def test_direct_row_match_beats_generic_sheet_name_bonus() -> None:
    sheet_only = _row("Transaction_Data", 1, "archive")
    direct = _row("Summary", 50, "Transaction 911.8")
    terms = search_terms("거래")

    assert relevance(direct, terms) > relevance(sheet_only, terms)
    assert search_rows((sheet_only, direct), "거래", 1) == [direct]


def _row(sheet_name: str, row_number: int, value: str) -> IndexedRow:
    return IndexedRow(
        sheet_name,
        row_number,
        (IndexedCell(sheet_name, f"A{row_number}", value, None),),
    )
