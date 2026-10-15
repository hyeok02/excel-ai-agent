from app.agent.query.verified_insight_constraints import required_concepts_match


def test_count_question_accepts_a_numeric_counter_in_the_fact() -> None:
    assert required_concepts_match(
        "네트워크 안정의 표시별 건수를 요약해줘",
        "네트워크 안정 표시는 x 7건, o 4건, 미입력 2건입니다.",
    )


def test_count_question_still_rejects_a_fact_without_a_count() -> None:
    assert not required_concepts_match(
        "네트워크 안정의 표시별 건수를 요약해줘",
        "네트워크 안정 표시는 확인이 필요합니다.",
    )


def test_hash_identifier_must_exist_in_the_fact() -> None:
    fact = "CVD 장비 17건 중 12건이 점검됐고 5건은 미점검 상태입니다."

    assert required_concepts_match("CVD #17의 IP는?", f"CVD #17: {fact}")
    assert not required_concepts_match("CVD #99의 IP는?", fact)
