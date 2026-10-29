"""A refused trend is answered only from complete, agreeing, evenly spaced source rows."""
from app.agent.query.source_series_answers import source_series_answer
from app.agent.query.verified_insight_constraints import required_concepts_match
from app.services.insights.facts.horizontal_series import extract_horizontal_series
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report
from tests.test_horizontal_series import cell, region
from tests.test_source_value_fallbacks import _book

UNITS = [[None, "Currency", None, "Magnitude"], [None, "USD", None, "Millions"]]


def _statement(dates=("2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"),
               revenue=(100, 110, 121, 133.1), chart=(110, 121, 133.1)):
    return [*UNITS, [], ["Period Ended", None, *dates], ["Revenue", None, *revenue],
            [], [], ["Chart Data", None, *dates[1:]], ["Revenue", None, *chart], ["Total Revenue", None, 10, 10, 10]]


def test_agreeing_rows_answer_the_whole_history_and_skip_a_growth_copy() -> None:
    summary, index = _book({"Results": _statement()})
    answer = source_series_answer("매출 추이 알려줘", summary, index)

    assert answer is not None
    assert answer.answer.index("100") < answer.answer.index("110") < answer.answer.index("133.1")
    assert "33.1" in answer.answer and "33.10%" in answer.answer and "증가" in answer.answer
    assert "원본 2곳" in answer.answer and " 10백만" not in answer.answer


def test_rows_that_disagree_on_a_shared_year_keep_the_refusal() -> None:
    summary, index = _book({"Results": _statement(chart=(110, 999, 133.1))})

    assert source_series_answer("Revenue 추이 알려줘", summary, index) is None


def test_a_skipped_year_is_a_gap_not_a_trend() -> None:
    dates = ("2021-12-31", "2022-12-31", "2024-12-31", "2025-12-31")
    summary, index = _book({"Results": _statement(dates, chart=(110, 121, 133.1))})

    assert source_series_answer("Revenue 추이 알려줘", summary, index) is None


def test_bounded_or_qualified_trends_stay_with_the_trend_path() -> None:
    summary, index = _book({"Results": _statement()})

    for question in ("2023년 이후 Revenue 추이 알려줘", "최근 3년 Revenue 추이", "분기별 Revenue 추이 알려줘"):
        assert source_series_answer(question, summary, index) is None


def test_a_superlative_question_needs_a_superlative_insight() -> None:
    item = {"title": "거래 규모", "topic": "거래 규모", "category": "metric",
            "fact": "비교 거래의 거래 규모 중앙값은 1,200백만 달러입니다."}

    assert not required_concepts_match("비교 거래 중 가장 큰 거래는?", item["fact"])
    assert required_concepts_match("가장 큰 거래는?", "가장 큰 거래는 DenizBank 인수입니다.")
    assert not required_concepts_match("가장 작은 거래는?", item["fact"])


def test_a_plain_row_copying_a_growth_rate_is_not_narrated_as_the_metric() -> None:
    dates = ("2024-01-31", "2025-01-31", "2026-01-31")
    rows = [("Revenue", (648125, 680985, 713163)), ("1 Year Growth (%)", (6.03, 5.07, 4.73)),
            ("Total Revenue", (6.03, 5.07, 4.73))]
    source = region([cell(f"{chr(66 + n)}1", day) for n, day in enumerate(dates)],
                    *[[cell(f"A{r}", label), *[cell(f"{chr(66 + n)}{r}", v) for n, v in enumerate(values)]]
                      for r, (label, values) in enumerate(rows, start=2)])
    facts = {"horizontal_series": extract_horizontal_series([source])}
    _, overview = horizontal_trend_report({"sheets": [{"name": "Summary", "business_facts": facts}]})

    assert "713,163" in overview and "Total Revenue" not in overview.split(".")[0]
