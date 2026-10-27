"""Real source execution for multiple operations, without model/network calls."""
import asyncio

import pytest

from app.agent.query.composite_execution import composite_answer
from app.agent.query.composite_models import CompositeQueryPlan, CompositeQuestionPart
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.question_formula_sources import prepare_formula_sources
from app.agent.query.tabular_routing import planned_tabular_answer
from tests.support.large_workbook_fixtures import offline, parsed, workbook, plan_for, equal


def fixture():
    summary, index, _ = parsed(workbook({"Records": [
        ["Department", "Amount", "Customer", "Status"],
        ["North", 10, "First", "active"], ["South", 20, "Second", "inactive"],
        ["North", 30, "First", "active"],
    ]}))
    return summary, prepare_formula_sources(summary, index)


def part(text, plan):
    return CompositeQuestionPart(source_text=text, kind="aggregation", tabular_query=plan)


def execute(question, sources, prefix, parts):
    calls = []

    async def callback(text, current, **options):
        calls.append(text)
        assert options["allow_composite"] is False and options["allow_replan"] is False
        return planned_tabular_answer(options["intent_override"], current.summary, current.index, text)

    intent = QuestionIntent(False, composite_query=CompositeQueryPlan(shared_prefix=prefix, parts=parts))
    result = asyncio.run(composite_answer(question, sources, intent, callback))
    return result, calls


def test_three_different_operations_share_original_filters_and_compute_independently():
    summary, sources = fixture()
    prefix = "Records 시트 Status가 active인 행"
    definitions = [
        ("Amount 합계", plan_for(summary, filters=[equal("D", "active")])),
        ("Amount 평균", plan_for(summary, statistic="average", filters=[equal("D", "active")])),
        ("Customer 중복 제외 건수", plan_for(summary, operation="distinct_count", columns=("C",),
                                        filters=[equal("D", "active")])),
    ]
    question = prefix + ": " + "; ".join(text for text, _ in definitions)
    answer, calls = execute(question, sources, prefix, [part(text, plan) for text, plan in definitions])
    assert answer.status == "answered" and answer.verification.level == "request_checked", answer.model_dump()
    assert "합계 40" in answer.answer and "평균 20" in answer.answer
    assert "중복 제외 개수 1" in answer.answer
    assert len(calls) == 3 and all(prefix in text for text in calls)
    assert any("문항 3" in item.label for item in answer.evidence)


def test_one_wrong_operation_is_excluded_without_discarding_correct_sum():
    summary, sources = fixture()
    parts = [part("Amount 합계", plan_for(summary)),
             part("Customer 중복 제외 건수", plan_for(summary, operation="row_count", columns=()))]
    answer, calls = execute("Records 시트: Amount 합계; Customer 중복 제외 건수", sources, "Records 시트", parts)
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "합계 60" in answer.answer and "확인 불가" in answer.answer and len(calls) == 2
    assert all("문항 1" in item.label for item in answer.evidence)


def test_a_part_cannot_drop_an_explicit_common_filter():
    summary, sources = fixture()
    prefix = "Records 시트 Status가 active인 행"
    parts = [part("Amount 합계", plan_for(summary, filters=[equal("D", "active")])),
             part("Amount 평균", plan_for(summary, statistic="average"))]
    answer, calls = execute(prefix + ": Amount 합계; Amount 평균", sources, prefix, parts)
    assert answer.status == "limited" and answer.verification.level != "request_checked"
    assert "합계 40" in answer.answer and "평균 20" not in answer.answer and len(calls) == 1


def test_unstated_natural_condition_inheritance_does_not_create_a_global_green_answer():
    summary, sources = fixture()
    parts = [part("Status가 active인 Amount 평균 구하고", plan_for(
        summary, statistic="average", filters=[equal("D", "active")])),
        part("Amount 최댓값 알려줘", plan_for(summary, statistic="max"))]
    answer, calls = execute("Status가 active인 Amount 평균 구하고, Amount 최댓값 알려줘", sources, "", parts)
    assert answer.status == "limited" and answer.verification.level == "source_checked", answer.model_dump()
    assert len(calls) == 1 and any("적용되는지" in note for note in answer.limitations)


def test_explicit_global_second_clause_does_not_inherit_a_local_filter():
    summary, sources = fixture()
    parts = [part("Status가 active인 Amount 합계", plan_for(summary, filters=[equal("D", "active")])),
             part("전체 행 Amount 평균", plan_for(summary, statistic="average"))]
    answer, calls = execute("Status가 active인 Amount 합계; 전체 행 Amount 평균", sources, "", parts)
    assert answer.status == "answered" and answer.verification.level == "request_checked", answer.model_dump()
    assert len(calls) == 2
