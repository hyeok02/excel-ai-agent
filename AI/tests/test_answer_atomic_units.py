"""Partial output must contain complete original claims, never label fragments."""
from app.agent.query.answer_clauses import clauses, supported_clauses


def test_quoted_labels_and_formatted_numbers_stay_intact() -> None:
    text = "'North. Annex, R and D'는 1,234.50입니다. 다음 값은 2입니다."

    assert clauses(text) == [
        "'North. Annex, R and D'는 1,234.50입니다", "다음 값은 2입니다",
    ]


def test_dot_inside_unquoted_label_is_not_a_sentence_boundary() -> None:
    text = "A.서비스의 값은 4입니다. 확인되지 않은 값은 999입니다."

    actual, trimmed = supported_clauses(text, lambda part: "999" not in part)

    assert (actual, trimmed) == ("A.서비스의 값은 4입니다.", True)


def test_quoted_label_cannot_survive_unsupported_value_as_a_fragment() -> None:
    text = "항목별로 보면 - 'North. Annex, R and D'의 건수는 999입니다."

    assert supported_clauses(text, lambda part: "999" not in part) == ("", True)


def test_list_items_remain_whole_and_preserve_formatting() -> None:
    text = "항목별 결과:\n- 'Alpha. Inspection': 3\n- 'Beta, Inspection': 999\n"

    actual, trimmed = supported_clauses(text, lambda part: "999" not in part)

    assert (actual, trimmed) == ("- 'Alpha. Inspection': 3", True)


def test_standalone_heading_does_not_survive_when_all_claims_fail() -> None:
    text = "# 항목별 결과\n항목별로 보면\n- Alpha: 999\n"

    assert supported_clauses(text, lambda part: "999" not in part) == ("", True)


def test_partial_table_retains_header_and_separator_for_valid_rows() -> None:
    text = "| 항목 | 수량 |\n| --- | ---: |\n| Alpha | 3 |\n| Beta | 999 |\n"

    actual, trimmed = supported_clauses(text, lambda part: "999" not in part)

    assert (actual, trimmed) == (
        "| 항목 | 수량 |\n| --- | ---: |\n| Alpha | 3 |", True,
    )


def test_empty_table_does_not_return_only_column_names() -> None:
    text = "| 항목 | 수량 |\n| --- | ---: |\n| Beta | 999 |\n"

    assert supported_clauses(text, lambda part: "999" not in part) == ("", True)


def test_valid_answer_is_not_reformatted() -> None:
    text = "### 결과\n\n- 'Alpha. Inspection': 3\n\n값은 3이며, 기록은 같습니다."

    assert supported_clauses(text, lambda part: True) == (text, False)


def test_markdown_table_separator_is_not_treated_as_a_factual_claim() -> None:
    assert clauses("| 항목 | 수량 |\n| --- | ---: |\n| Alpha | 3 |") == [
        "| 항목 | 수량 |", "| Alpha | 3 |",
    ]
