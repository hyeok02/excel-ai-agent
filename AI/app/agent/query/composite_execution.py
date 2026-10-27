"""Bounded independent execution of exact original subquestions."""
from app.agent.query.composite_answers import compose_answers, unresolved_part
from app.agent.query.composite_split import split_compound_question, dependent_part
from app.agent.query.intent_models import QuestionIntent, QuestionIntentDraft
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.composite_scope import ambiguous_local_scope
from app.agent.query.question_formula_evidence import finish_formula_answer
from app.agent.query.interpretation_answers import finish_interpretation_answer


async def composite_answer(question, sources, intent, answer_prepared):
    split = split_compound_question(question, sources)
    proposed = getattr(intent, "composite_query", None)
    if split is None:
        return (unresolved_part(question, "제안된 복합 질문을 원문의 독립된 질문들과 대조하지 못했습니다.")
                if proposed is not None else None)
    if split.error:
        return unresolved_part(question, split.error)
    if dependent_part(split.shared_prefix):
        return unresolved_part(question, "공통 조건이 이전 결과를 가리켜 원본 범위를 확정하지 못했습니다.")
    if proposed is not None and not _matches_original(proposed, split, intent):
        return unresolved_part(question, "질문 분해 과정에서 원문의 일부 조건·문항이 바뀌거나 빠져 실행하지 않았습니다.")
    answers = []
    for position, text in enumerate(split.parts):
        current = split.question_for(position)
        if dependent_part(text):
            answers.append(unresolved_part(current, "앞 문항의 결과를 가리키는 범위를 확정하지 못했습니다. 대상이나 조건을 직접 지정해 주세요."))
            continue
        if ambiguous_local_scope(split, position, proposed, answers, sources):
            answers.append(unresolved_part(current, "앞 문항의 조건이 이 문항에도 적용되는지 명확하지 않습니다. 공통 조건을 ':' 앞에 적거나 각 문항에 조건을 지정해 주세요."))
            continue
        override = _part_intent(proposed.parts[position]) if proposed is not None else None
        try:
            answer = await answer_prepared(current, sources, intent_override=override,
                                           allow_replan=False, allow_composite=False)
            answer = finish_interpretation_answer(finish_formula_answer(answer, sources))
        except Exception as error:
            raise_for_quota_exhaustion(error)
            answer = unresolved_part(current, "이 문항을 원본에서 계산·검증하지 못했습니다.")
        # A callback must not quietly answer a different question or context.
        if answer.question != current or answer.resolved_question not in (None, current):
            answer = unresolved_part(current, "부분 질문의 범위가 실행 중 달라져 결과를 표시하지 않았습니다.")
        answers.append(answer)
    return compose_answers(question, split, answers)


def _matches_original(proposed, split, intent):
    return (proposed.shared_prefix == split.shared_prefix
            and tuple(part.source_text for part in proposed.parts) == split.parts
            and not any(getattr(intent, field, None) for field in
                        ("tabular_query", "relational_query", "header_relation")))


def _part_intent(part):
    return QuestionIntent.from_draft(QuestionIntentDraft(
        scope=part.scope, kind=part.kind, targets=part.targets, tabular_query=part.tabular_query,
        relational_query=part.relational_query, header_relation=part.header_relation,
    ))
