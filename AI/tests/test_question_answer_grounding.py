from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.query.answer_grounding import (
    answer_is_grounded,
    verified_fallback_answer,
    verified_support_references,
)


def test_grounded_answer_uses_cited_labels_and_values() -> None:
    evidence = [
        _evidence("A2", "상품", "노트북"),
        _evidence("B2", "1월", 10),
    ]

    assert answer_is_grounded(
        "노트북의 1월 값은 10입니다.", evidence, _execution()
    )


def test_unsupported_non_numeric_claim_is_blocked() -> None:
    evidence = [_evidence("B2", "1월", 10)]

    assert not answer_is_grounded(
        "이 회사는 파산 위험이 높습니다.", evidence, _execution()
    )


def test_covered_verified_fact_supplies_safe_business_vocabulary() -> None:
    evidence = [
        _evidence("H70", "Company Name", "MTGE"),
        _evidence("AP66", "EV / EBITDA", 9.99),
        _evidence("AP70", "EV / EBITDA", 5.09),
    ]
    fact = {
        "title": "EBITDA 대비 거래가격: 비교군 중앙값보다 낮음",
        "fact": "MTGE의 거래가치/EBITDA 배수는 비교군 중앙값보다 낮습니다.",
        "required_references": ["거래!H70", "거래!AP66", "거래!AP70"],
    }

    assert answer_is_grounded(
        fact["fact"], evidence, _execution([fact])
    )


def test_verified_fact_adds_omitted_range_support() -> None:
    evidence = [
        _evidence("AP66", "EV / EBITDA 중앙값", 9.99),
        _evidence("AP70", "MTGE EV / EBITDA", 5.09),
    ]
    fact = {
        "title": "EBITDA 배수 비교",
        "fact": "MTGE의 EBITDA 배수는 비교군보다 49.0% 낮습니다.",
        "support_references": ["거래!AP66", "거래!AP70", "거래!AP54:AP63"],
    }
    execution = _execution([fact])

    assert verified_support_references("EBITDA 비교", evidence, execution) == (
        fact["support_references"]
    )
    assert verified_fallback_answer("EBITDA 비교", evidence, execution) is None


def test_cited_english_header_allows_its_korean_glossary_name_only() -> None:
    services = [_evidence("W107", "Department", "Services")]
    research = [_evidence("N107", "Department", "Research & Development")]
    question = "어느 부서가 가장 많이 감소했어?"

    assert answer_is_grounded(
        "서비스 부서가 가장 많이 감소했습니다.", services, _execution(), question
    )
    assert not answer_is_grounded(
        "서비스 부서가 가장 많이 감소했습니다.", research, _execution(), question
    )


def _evidence(reference: str, description: str, value: object):
    return SimpleNamespace(
        sheet_name="거래" if reference != "A2" and reference != "B2" else "매출현황",
        reference=reference,
        description=description,
        value=value,
        formula=None,
    )


def _execution(facts=None):
    steps = []
    if facts is not None:
        result = SimpleNamespace(data={"verified_insights": facts})
        steps.append(SimpleNamespace(status=AgentStepStatus.SUCCEEDED, result=result))
    return SimpleNamespace(steps=steps)
