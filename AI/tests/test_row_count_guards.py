from app.agent.tools.workbook_row_counts import build_row_count


def test_headcount_is_not_mistaken_for_an_english_count_request() -> None:
    assert build_row_count(
        [], {}, "What was R&D headcount in February 2023?"
    ) is None
