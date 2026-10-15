"""기간별 수치 표에 같은 뜻을 다르게 물어도 같은 답이 나오는지.

패러프레이즈 테스트가 점검표(o/x) 모양만 보고 있어서, 머리글 판별을 고치다가
조회 경로를 깨뜨린 적이 있다. 수치 추이 표 모양도 같이 묶어 둔다.
"""
import pytest

from app.agent.tools.workbook_headers import build_header_context
from app.agent.tools.workbook_comparisons import build_time_series_comparison
from app.agent.tools.workbook_metric_changes import (
    build_metric_change,
    build_metric_count,
)
from tests.support.series_rows import SHEET, rows

NAMED_METRIC = (
    "Services 어떻게 변했어?",
    "Services 얼마나 줄었어?",
    "Services 인원 변화 알려줘",
)


def _comparison(question: str):
    found = list(rows())
    headers = build_header_context(tuple(found), found)
    return build_time_series_comparison(found, headers, question, None, {})


def test_the_table_is_read_as_a_time_series() -> None:
    comparison = _comparison("Services 인원 알려줘")

    assert comparison
    assert comparison["sheet_name"] == SHEET
    assert {str(metric["header"]) for metric in comparison["metrics"]} >= {
        "Services", "Research & Development",
    }


@pytest.mark.parametrize("question", NAMED_METRIC)
def test_every_wording_picks_the_named_metric(question: str) -> None:
    found = build_metric_change(_comparison(question), question)

    assert found is not None, question
    assert found["header"] == "Services"
    assert found["start_value"] == 1277
    assert found["end_value"] == 1081


def test_plain_named_value_uses_a_snapshot_instead_of_a_change() -> None:
    from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot

    question = "Services 인원 알려줘"
    assert build_metric_change(_comparison(question), question) is None
    found = build_metric_snapshot(_comparison(question), question)
    assert found is not None and found["metrics"][0]["value"] == 1081


def test_a_question_naming_no_metric_is_left_alone() -> None:
    question = "이 파일 뭐야?"

    assert build_metric_change(_comparison(question), question) is None


def test_the_model_target_finds_a_metric_the_wording_misses() -> None:
    # 머리글이 'Services'인데 질문은 '서비스'라 글자로는 겹치지 않는다.
    question = "서비스 부서 인원 알려줘"

    from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot

    found = build_metric_snapshot(_comparison(question), question, ("Services",))

    assert found is not None
    assert found["metrics"][0]["header"] == "Services"


def test_r_and_d_abbreviation_selects_research_and_development() -> None:
    question = "R&D 직원 수 변화"
    found = build_metric_change(_comparison(question), question)

    assert found is not None
    assert found["header"] == "Research & Development"


def test_counts_the_metrics_when_the_question_asks_how_many() -> None:
    question = "부서가 총 몇 개야?"
    comparison = _comparison(question)
    if comparison.get("metric_group") != "department":
        pytest.skip("이 표는 부서 묶음으로 읽히지 않는다")

    found = build_metric_count(comparison, question)

    assert found["count"] >= 2
