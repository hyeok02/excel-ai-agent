"""Compose checked subanswers without borrowing their badge for failed parts."""
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification


def unresolved_part(question, reason):
    return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                          selected_tools=["composite_question"], evidence=[], limitations=[reason])


def compose_answers(question, split, answers):
    evidence, sections, limitations, tools = [], [], [], ["composite_question"]
    verified = 0
    complete = len(answers) == len(split.parts)
    for position, (text, answer) in enumerate(zip(split.parts, answers), 1):
        usable = (answer.status != "insufficient_evidence" and answer.verification.level != "unverified"
                  and bool(answer.evidence))
        checked = (usable and answer.status == "answered" and answer.verification.level == "request_checked"
                   and "request_alignment" in answer.verification.checks and not answer.limitations)
        complete = complete and checked
        verified += bool(usable)
        label = "요청·원본 확인" if checked else "일부 원본 확인" if usable else "확인 불가"
        content = answer.answer if usable else "이 부분은 원본과 요청 범위를 확정하지 못했습니다."
        references = []
        if usable:
            for item in answer.evidence:
                evidence.append(item.model_copy(update={"label": f"문항 {position} · {item.label}"}))
                references.append(f"#{len(evidence)}")
        proof = "\n원본 근거: " + ", ".join(references) if references else ""
        sections.append(f"{position}. {text}\n[{label}] {content}{proof}")
        limitations.extend(f"문항 {position}: {message}" for message in answer.limitations)
        if not checked and not answer.limitations:
            limitations.append(f"문항 {position}: 답변 전체의 요청 일치와 원본 근거를 확인하지 못했습니다.")
        tools.extend(answer.selected_tools)
    if split.shared_prefix:
        sections.insert(0, f"공통 범위·조건: {split.shared_prefix}")
    if not complete:
        limitations.insert(0, "일부 질문만 확인했습니다. 확인하지 못한 부분을 포함해 전체 답변이 검증된 것은 아닙니다.")
    level = "request_checked" if complete else "source_checked" if verified else "unverified"
    checks = ["compound_request_coverage", "independent_subquestions", f"compound_parts_{len(answers)}"] if complete else []
    if complete:
        checks.extend(check for answer in answers for check in answer.verification.checks)
    return QuestionAnswer(
        question=question, answer="\n\n".join(sections),
        status="answered" if complete else "limited" if verified else "insufficient_evidence",
        confidence=min((answer.confidence for answer in answers), default=0),
        selected_tools=list(dict.fromkeys(tools)), evidence=evidence,
        limitations=list(dict.fromkeys(limitations)),
        verification=QuestionAnswerVerification(level=level, checks=list(dict.fromkeys(checks))),
    )
