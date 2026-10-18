from app.agent.query.metric_observation_periods import requested_periods


def test_identical_date_and_grain_mentions_collapse_without_dropping_qualifiers():
    question = "2024년 9월 30일 회계연도 기준으로: 2024년 9월 30일 Operating Income은?"
    periods = requested_periods(question)
    assert len(periods) == 1
    assert (periods[0].year, periods[0].month, periods[0].day, periods[0].grain) == (2024, 9, 30, "annual")


def test_equal_dates_with_distinct_reporting_grain_are_not_deduplicated():
    periods = requested_periods("2024년 9월 30일 회계연도와 2024년 9월 30일 분기 Operating Income 알려줘")
    assert len(periods) == 2
    assert {period.grain for period in periods} == {"annual", "quarter"}


def test_equal_dates_with_distinct_scenarios_are_not_deduplicated():
    periods = requested_periods("2024년 실제 Revenue와 2024년 예상 Revenue 알려줘")
    assert len(periods) == 2
    assert {period.scenario for period in periods} == {"actual", "estimate"}


def test_explicit_same_period_comparison_keeps_both_operands():
    periods = requested_periods("2024년 회계연도 Operating Income과 2024년 회계연도 Operating Income 차이는?")
    assert len(periods) == 2 and periods[0] == periods[1]
