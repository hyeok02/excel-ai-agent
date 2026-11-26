"""Rows picked by their order or by an average: '가장 비싼 상품', '수학 상위 3명', '연봉이 평균보다 낮은'.

The model names the column and the order; the ranking and the average are computed here from every row the
other conditions kept. A tie at the cut ('상위 3명' when the 3rd and 4th share a score) or a non-number in the
column stops the rule instead of guessing which rows the request meant.
"""
import re
from decimal import Decimal

from app.agent.writeback.rule_columns import ORDER

RANK_WORDS = re.compile(r"가장|제일|최고|최저|상위|하위|평균\s*(?:보다|이상|이하|미만|초과)|\btop\s*\d*\b|\bbottom\b|"
                        r"highest|lowest|largest|smallest|cheapest|most expensive|above average|below average", re.I)


def ranked_rows(rows, rule, resolve, table):
    """(rows, problem) after the rule's average conditions and rank."""
    for item in rule.average_filters:
        column = resolve(item.column_id, table)
        values = _numbers(rows, column)
        if values is None:
            return None, "평균과 비교할 열에 숫자가 아닌 값이 있습니다."
        mean = sum(values) / len(values)
        rows = [row for row, value in zip(rows, values) if ORDER[item.operator](value, mean)]
    if rule.rank is not None:
        column = resolve(rule.rank.column_id, table)
        values = _numbers(rows, column)
        if values is None:
            return None, "순위를 매길 열에 숫자가 아닌 값이 있습니다."
        ordered = sorted(zip(rows, values), key=lambda pair: pair[1], reverse=rule.rank.order == "highest")
        count = rule.rank.count
        if count < len(ordered) and ordered[count - 1][1] == ordered[count][1]:
            return None, f"{count}번째와 {count + 1}번째 값이 같아 순위로 고를 행을 정할 수 없습니다."
        rows = [row for row, _ in ordered[:count]]
    return rows, None


def rank_text(rule, columns, resolve, table):
    parts = [f"‘{columns[resolve(item.column_id, table)].display_header}’ {'>' if 'greater' in item.operator else '<'} 평균"
             for item in rule.average_filters]
    if rule.rank is not None:
        word = "가장 큰" if rule.rank.order == "highest" else "가장 작은"
        parts.append(f"‘{columns[resolve(rule.rank.column_id, table)].display_header}’ {word} {rule.rank.count}개")
    return ", ".join(parts)


def _numbers(rows, column):
    values = [row.values.get(column) if column else None for row in rows]
    if not values or any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in values):
        return None
    return [Decimal(str(value)) for value in values]
