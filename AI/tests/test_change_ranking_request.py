import pytest

from app.agent.query.change_ranking_request import parse_change_ranking_request


@pytest.mark.parametrize("question,basis,percent", [
    ("전체 기간 중 인원이 제일 많이 감소한 부서는 어디야?", "auto", False),
    ("처음과 마지막을 비교해서 가장 많이 감소한 부서는?", "net", False),
    ("시작값 대비 끝값의 감소율이 가장 큰 부서는?", "net", True),
    ("고점 대비 현재 인원이 가장 많이 감소한 부서는?", "extreme_to_latest", False),
    ("인접 분기 사이 인원이 가장 많이 감소한 부서는?", "adjacent", False),
    ("기간 중 최대 낙폭을 기록한 부서는?", "max_drawdown", False),
    ("기간 중 고점 대비 이후 저점까지 가장 많이 감소한 부서는?", "max_drawdown", False),
    ("전체 기간 중 인원이 가장 많이 늘어난 부서는?", "auto", False),
    ("Which department had the largest percentage decline from first to last?", "net", True),
])
def test_explicit_basis_and_ranking_request(question, basis, percent):
    request = parse_change_ranking_request(question)
    assert request and request.basis == basis and request.percent is percent
    assert request.group == "department"


@pytest.mark.parametrize("question", ["매출은 얼마야?", "인원 합계를 알려줘", "부서별 추이를 보여줘"])
def test_nonranking_questions_remain_with_existing_handlers(question):
    assert parse_change_ranking_request(question) is None
