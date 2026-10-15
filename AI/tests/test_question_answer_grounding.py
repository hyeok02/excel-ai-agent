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


def test_answer_cannot_ignore_an_explicit_hash_identifier() -> None:
    evidence = [_evidence("A2", "CVD 장비", "CVD #1")]

    assert not answer_is_grounded(
        "CVD 장비 현황입니다.", evidence, _execution(), "CVD #99의 IP는?"
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


def test_range_only_fact_is_discovered_from_two_cited_point_cells() -> None:
    evidence = [
        _evidence("W108", "2025-06 Services 인원", 5417, "인원"),
        _evidence("N108", "2025-06 Research & Development 인원", 1816, "인원"),
    ]
    fact = {
        "title": "부서별 인원 변화",
        "fact": "Services 부서는 6,101명에서 5,417명으로 684명 감소했습니다.",
        "support_references": ["인원!E127:AI127", "인원!E108:AI108"],
    }

    assert verified_support_references(
        "부서별 인원 변화를 알려줘", evidence, _execution([fact])
    ) == fact["support_references"]


def test_one_point_does_not_unlock_a_range_only_verified_fact() -> None:
    evidence = [_evidence("W108", "2025-06 Services 인원", 5417, "인원")]
    fact = {
        "title": "부서별 인원 변화",
        "fact": "Services 부서는 6,101명에서 5,417명으로 684명 감소했습니다.",
        "support_references": ["인원!E127:AI127", "인원!E108:AI108"],
    }

    assert verified_support_references(
        "부서별 인원 변화를 알려줘", evidence, _execution([fact])
    ) == []


def test_unrelated_question_does_not_unlock_a_range_only_verified_fact() -> None:
    evidence = [
        _evidence("W108", "2025-06 Services 인원", 5417, "인원"),
        _evidence("N108", "2025-06 Research & Development 인원", 1816, "인원"),
    ]
    fact = {
        "title": "부서별 인원 변화",
        "fact": "Services 부서는 6,101명에서 5,417명으로 684명 감소했습니다.",
        "support_references": ["인원!E127:AI127", "인원!E108:AI108"],
    }

    assert verified_support_references(
        "영업이익은 얼마야?", evidence, _execution([fact])
    ) == []


def test_cited_english_header_allows_its_korean_glossary_name_only() -> None:
    services = [_evidence("W107", "Department", "Services"), _evidence("W108", "Headcount", 10)]
    research = [_evidence("N107", "Department", "Research & Development"), _evidence("N108", "Headcount", 10)]
    question = "어느 부서가 가장 많이 감소했어?"

    assert answer_is_grounded(
        "서비스 부서의 인원은 10명입니다.", services, _execution(), question
    )
    assert not answer_is_grounded(
        "서비스 부서의 인원은 10명입니다.", research, _execution(), question
    )


def _evidence(
    reference: str, description: str, value: object, sheet_name: str | None = None
):
    return SimpleNamespace(
        sheet_name=sheet_name or (
            "거래" if reference != "A2" and reference != "B2" else "매출현황"
        ),
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
