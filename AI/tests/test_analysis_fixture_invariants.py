"""픽스처가 늘어나면 자동으로 함께 늘어나는 불변식.

파일마다 기대값을 손으로 적지 않아도, 어떤 워크북에서도 참이어야 하는
성질을 픽스처 전체에 걸어 둔다.
"""

from pathlib import Path

import pytest

from app.agent.query import build_workbook_data_index
from app.agent.query.question_validation import vague_question_answer
from app.services.insights.context import build_workbook_context
from app.services.insights.fact_trends import is_plain_text
from app.services.insights.quality import metric_changes, subject_name
from app.services.workbook_parser import parse_workbook
from tests.support.analysis_regression import (
    DROP,
    load_analysis_fixture_cases,
    review_point_verdict,
)

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "analysis"
CASES = load_analysis_fixture_cases(FIXTURE_DIRECTORY)
CASE_IDS = [case.name for case in CASES]
UNKNOWN_TERM = "젭라흐크"
UNVERIFIABLE_REVIEW_POINT = "값이 987654까지 늘었습니다."


def _parsed(case):
    content = case.workbook_path.read_bytes()
    summary = parse_workbook(case.workbook_path.name, content)
    return summary, content


def _index(summary, content):
    return build_workbook_data_index(
        summary.filename, content, {sheet.name for sheet in summary.sheets}
    )


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_subject_is_never_a_number_or_date(case) -> None:
    summary, _ = _parsed(case)

    subject = subject_name(build_workbook_context(summary))

    assert subject is None or is_plain_text(subject)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_metric_names_always_pass_question_validation(case) -> None:
    """지표 이름은 워크북이 직접 제공한 단어이므로 되물으면 안 된다."""
    summary, content = _parsed(case)
    index = _index(summary, content)
    context = build_workbook_context(summary)

    for change in metric_changes(context):
        metric = str(change["metric"])
        assert vague_question_answer(metric, index) is None, metric


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_term_absent_from_the_workbook_always_asks_back(case) -> None:
    summary, content = _parsed(case)

    assert vague_question_answer(UNKNOWN_TERM, _index(summary, content)) is not None


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_unverifiable_number_is_always_dropped(case) -> None:
    summary, _ = _parsed(case)
    context = build_workbook_context(summary)

    assert review_point_verdict(context, UNVERIFIABLE_REVIEW_POINT) == DROP
