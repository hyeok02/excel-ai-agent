from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.query.numeric_support import answer_units_supported


def _evidence(value, description="Amount"):
    return SimpleNamespace(
        sheet_name="Sheet1",
        reference="A1",
        value=value,
        formula=None,
        description=description,
    )


def _execution(result=None, end=80):
    calculations = []
    if result is not None:
        calculations.append(
            {
                "operation": "percent_change",
                "operand_references": ["Sheet1!A1", "Sheet1!A2"],
                "operand_values": [100, end],
                "result": result,
                "unit": "percent",
            }
        )
    step_result = SimpleNamespace(data={"calculations": calculations})
    step = SimpleNamespace(status=AgentStepStatus.SUCCEEDED, result=step_result)
    return SimpleNamespace(steps=[step])


def test_verified_percent_rejects_hundredfold_claim() -> None:
    evidence = [_evidence(100), _evidence(80)]
    evidence[1].reference = "A2"
    execution = _execution(-20)

    assert answer_units_supported("20% 감소", evidence, execution)
    assert not answer_units_supported("2,000% 감소", evidence, execution)


def test_fractional_percent_source_has_one_display_scale() -> None:
    evidence = [_evidence(0.1, "Margin (%)")]

    assert answer_units_supported("Margin은 10%입니다.", evidence, _execution())
    assert not answer_units_supported("Margin은 0.1%입니다.", evidence, _execution())


def test_percent_context_does_not_match_word_substring() -> None:
    evidence = [_evidence(10, "Corporate revenue")]

    assert not answer_units_supported(
        "Corporate revenue는 10%입니다.", evidence, _execution()
    )


def test_explicit_percent_result_allows_display_rounding() -> None:
    evidence = [_evidence(100), _evidence(79.76)]
    evidence[1].reference = "A2"

    assert answer_units_supported(
        "약 20.2% 감소", evidence, _execution(-20.24, end=79.76)
    )
