from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agent.execution import AgentStepStatus
from app.agent.query.calculations import verified_calculations
from app.agent.query.numeric_support import (
    answer_units_supported,
    supported_answer_numbers,
)


def _evidence(*values, percent: bool = False):
    description = "Margin (%)" if percent else "Amount"
    return [
        SimpleNamespace(
            sheet_name="Sheet1",
            reference=f"A{index}",
            value=value,
            formula="=1000+234",
            description=description,
        )
        for index, value in enumerate(values, 1)
    ]


def _execution(calculations, status=AgentStepStatus.SUCCEEDED):
    result = SimpleNamespace(data={"calculations": calculations})
    return SimpleNamespace(steps=[SimpleNamespace(status=status, result=result)])


def _calculation(operation, values, result, unit="number", references=None):
    return {
        "operation": operation,
        "operand_references": references or [
            f"Sheet1!A{index}" for index in range(1, len(values) + 1)
        ],
        "operand_values": values,
        "result": result,
        "unit": unit,
    }


@pytest.mark.parametrize(
    ("operation", "values", "result", "unit"),
    [
        ("difference", [10, 20], 10, "number"),
        ("percent_change", [100, 80], -20, "percent"),
        ("sum", [10, 20], 30, "number"),
        ("average", [10, 20], 15, "number"),
        ("median", [9, 1, 3], 3, "number"),
        ("min", [9, 1, 3], 1, "number"),
        ("max", [9, 1, 3], 9, "number"),
        ("count", [9, 1, 3], 3, "count"),
    ],
)
def test_allows_recalculated_whitelist_results(operation, values, result, unit) -> None:
    evidence = _evidence(*values)
    execution = _execution([_calculation(operation, values, result, unit)])

    verified = verified_calculations(evidence, execution)
    supported = supported_answer_numbers("", evidence, execution)

    assert [item.result for item in verified] == [Decimal(str(result))]
    assert abs(Decimal(str(result))) in supported


@pytest.mark.parametrize(
    "calculation",
    [
        _calculation("product", [10, 20], 200),
        _calculation("average", [10, 20], 999),
        _calculation(
            "average", [10, 20], 15,
            references=["Sheet1!A1", "Sheet1!A3"],
        ),
    ],
)
def test_rejects_untrusted_or_incomplete_calculations(calculation) -> None:
    supported = supported_answer_numbers(
        "", _evidence(10, 20), _execution([calculation])
    )

    assert Decimal(str(abs(calculation["result"]))) not in supported


def test_ignores_formula_and_description_numbers() -> None:
    evidence = _evidence(10)
    evidence[0].description = "2024 amount"

    supported = supported_answer_numbers("", evidence, _execution([]))

    assert supported == {Decimal("10")}
    assert Decimal("1000") not in supported
    assert Decimal("234") not in supported
    assert Decimal("2024") not in supported


def test_count_accepts_cited_non_numeric_cells() -> None:
    evidence = _evidence("NA", 2.31, "NA")
    calculation = _calculation("count", ["NA", 2.31, "NA"], 3, "count")

    verified = verified_calculations(evidence, _execution([calculation]))

    assert [item.result for item in verified] == [Decimal("3")]


def test_rejects_percent_unit_from_bare_number() -> None:
    assert not answer_units_supported(
        "Amount is 10%.", _evidence(10), _execution([])
    )


def test_accepts_percent_typed_value_or_verified_percent_calculation() -> None:
    assert answer_units_supported(
        "Margin is 10%.", _evidence(10, percent=True), _execution([])
    )
    assert answer_units_supported(
        "Margin is 10%.", _evidence(0.1, percent=True), _execution([])
    )
    evidence = _evidence(100, 80)
    calculation = _calculation("percent_change", [100, 80], -20, "percent")
    assert answer_units_supported(
        "20% decrease", evidence, _execution([calculation])
    )
    assert not answer_units_supported(
        "20% decrease", evidence[:1], _execution([calculation])
    )


def test_ignores_calculation_from_failed_tool_step() -> None:
    calculation = _calculation("average", [10, 20], 15)
    supported = supported_answer_numbers(
        "", _evidence(10, 20),
        _execution([calculation], AgentStepStatus.FAILED),
    )

    assert Decimal("15") not in supported
