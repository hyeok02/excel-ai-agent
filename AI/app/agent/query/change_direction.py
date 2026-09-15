"""답변이 말한 증감 방향이 원본 값의 변화 방향과 같은지 확인한다.

차이와 증감률은 절댓값으로 대조하므로, 방향을 따로 보지 않으면
"6,101명에서 5,417명으로 684명 증가"처럼 뒤집힌 문장도 통과한다.
"A에서 B로 …했다" 형태, 즉 한 절에 인용 셀 값이 정확히 두 개 있을 때만
판단한다. 값이 더 많으면 무엇과 무엇을 비교했는지 알 수 없어 넘긴다.
"""
from app.agent.query.answer_clauses import clauses, stated_direction
from app.agent.query.derived_numbers import stated_cell_values


def answer_directions_supported(answer: str, evidence: list[object]) -> bool:
    for clause in clauses(answer):
        direction = stated_direction(clause)
        if direction is None:
            continue
        values = stated_cell_values(clause, evidence)
        if len(values) != 2:
            continue
        change = values[1] - values[0]
        if change == 0 or (change > 0) is not (direction == "increase"):
            return False
    return True
