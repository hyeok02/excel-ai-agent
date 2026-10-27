"""Exact original coverage is a code check, not a model paraphrase promise."""
import pytest

from app.agent.query.composite_split import split_compound_question, dependent_part
from app.agent.query.composite_models import CompositeQueryPlan, CompositeQuestionPart
from app.agent.query.intent_models import QuestionIntent, QuestionIntentDraft


@pytest.mark.parametrize("question,parts", [
    ("매출 합계; 고객 수", ("매출 합계", "고객 수")),
    ("매출 합계\n고객 수", ("매출 합계", "고객 수")),
    ("매출 합계는? 고객 수는?", ("매출 합계는?", "고객 수는?")),
    ("인원 변화를 비교하고, 부서별 건수를 알려줘", ("인원 변화를 비교하고", "부서별 건수를 알려줘")),
    ("금액을 계산하고 그리고 고객 수를 알려줘", ("금액을 계산하고", "고객 수를 알려줘")),
    ("매출은? '고객' 수는?", ("매출은?", "'고객' 수는?")),
])
def test_only_explicit_clauses_are_split_without_rewriting(question, parts):
    split = split_compound_question(question)
    assert split.parts == parts and split.shared_prefix == "" and split.error is None


@pytest.mark.parametrize("question", [
    "상태가 'active;inactive'인 매출 합계", "Category='Why? Because'인 건수",
    "상태 active 그리고 매출 100 이상인 행 수", "State is Seoul and Amount > 100 count",
    "Sales (A;B) 합계", "A1:B10 합계", "매출과 비용 합계",
])
def test_filters_source_values_and_headers_are_not_questions(question):
    assert split_compound_question(question) is None


def test_common_scope_prefix_is_inherited_exactly_by_every_clause():
    split = split_compound_question("Records 시트 Status가 'active'인 행: Amount 합계; Customer 중복 제외 건수")
    assert split.shared_prefix == "Records 시트 Status가 'active'인 행"
    assert split.question_for(1) == "Records 시트 Status가 'active'인 행 Customer 중복 제외 건수"


def test_source_ranges_and_times_are_not_shared_prefixes():
    assert split_compound_question("Sheet1!A1:B10 합계; 고객 수").shared_prefix == ""
    assert split_compound_question("10:30 값; 11:30 값").shared_prefix == ""


def test_all_more_than_four_clauses_are_retained_but_not_executed():
    split = split_compound_question("A; B; C; D; E")
    assert len(split.parts) == 5 and split.error


@pytest.mark.parametrize("text", ["그중 상위 3명", "위 결과의 평균", "해당 고객 수", "among those top 3"])
def test_dependent_clauses_cannot_be_reinterpreted_as_global_questions(text):
    assert dependent_part(text)


def test_composite_intent_never_becomes_a_whole_file_summary():
    plan = CompositeQueryPlan(parts=[CompositeQuestionPart(source_text="매출 합계"),
                                    CompositeQuestionPart(source_text="고객 수")])
    intent = QuestionIntent.from_draft(QuestionIntentDraft(scope="whole_workbook", kind="summary", composite_query=plan))
    assert intent.composite_query is plan
    assert not intent.whole_workbook and not intent.wants_a_summary
