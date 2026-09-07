from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.answer_validation import validate_answer
from app.agent.query.models import QuestionAnswerDraft, QuestionAnswerStatus
from app.services.provenance import EvidenceKind


def test_uses_verified_fact_when_model_adds_unsupported_interpretation() -> None:
    peer_values = ["NA", "NA", 2.31, "NA", "NA", 16.88, "NA", "NA", 9.99, "NA"]
    evidence = [
        _evidence("AP66", 9.99, "EV / EBITDA 비교거래 중앙값"),
        _evidence("AP70", 5.09, "MTGE EV / EBITDA"),
        *[
            _evidence(f"AP{row}", value, "비교거래 EV / EBITDA")
            for row, value in zip(range(54, 64), peer_values)
        ],
    ]
    canonical = (
        "MTGE의 EBITDA 배수는 5.09배로, 비교거래 10건 중 값이 있는 3건의 "
        "중앙값 9.99배보다 4.90배, 즉 49.0% 낮습니다."
    )
    calculations = [
        _calculation("difference", ["AP66", "AP70"], [9.99, 5.09], -4.9, "multiple"),
        _calculation(
            "percent_change", ["AP66", "AP70"], [9.99, 5.09], -49.049049049, "percent"
        ),
        _calculation(
            "count", [f"AP{row}" for row in range(54, 64)], peer_values, 10, "count"
        ),
        _calculation("count", ["AP56", "AP59", "AP62"], [2.31, 16.88, 9.99], 3, "count"),
    ]
    fact = {
        "title": "EBITDA 배수 비교",
        "fact": canonical,
        "support_references": ["거래!AP66", "거래!AP70", "거래!AP54:AP63"],
    }
    execution = _execution(evidence, calculations, fact)
    draft = QuestionAnswerDraft(
        answer=canonical + " 따라서 가격은 절반 수준입니다.",
        evidence=["거래!AP66", "거래!AP70"],
        confidence=0.95,
    )

    answer = validate_answer("MTGE EBITDA 배수를 비교해줘", draft, execution, False)

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == canonical
    assert {item.reference for item in answer.evidence} >= {"AP54", "AP63", "AP66", "AP70"}


def test_rejects_values_bound_to_the_wrong_row_label() -> None:
    evidence = [
        _evidence("A2", "노트북", "상품"),
        _evidence("B2", 10, "수량"),
        _evidence("A3", "휴대폰", "상품"),
        _evidence("B3", 20, "수량"),
    ]
    draft = QuestionAnswerDraft(
        answer="노트북은 20개이고 휴대폰은 10개입니다.",
        evidence=["거래!A2:B3"],
        confidence=0.9,
    )

    answer = validate_answer("상품별 수량은?", draft, _execution(evidence, [], {}), False)

    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE


def _evidence(reference, value, description):
    return AgentExecutionEvidence(
        kind=EvidenceKind.CELL,
        sheet_name="거래",
        reference=reference,
        description=description,
        value=value,
    )


def _calculation(operation, refs, values, result, unit):
    return {
        "operation": operation,
        "operand_references": [f"거래!{reference}" for reference in refs],
        "operand_values": values,
        "result": result,
        "unit": unit,
    }


def _execution(evidence, calculations, fact):
    result = SimpleNamespace(
        evidence=evidence,
        data={"calculations": calculations, "verified_insights": [fact]},
    )
    step = SimpleNamespace(
        status=AgentStepStatus.SUCCEEDED,
        result=result,
        tool_name="search_workbook_data",
    )
    return SimpleNamespace(steps=[step])
