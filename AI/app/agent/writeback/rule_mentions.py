"""Source names the request uses to pick rows that no rule reads.

"영업 부서 사원들 연봉을 300만원씩 올려줘" read as 부서 = 영업 alone would raise every 영업 salary; 사원 is a
직급 in the table and the request names it before the value. Such a reading is not applied: the request is
handed back with the name it left out. Only text values written before the value part are read.
"""
import re
from datetime import datetime

from app.agent.query.tabular_filters import same_value
from app.agent.writeback.natural_operations import ASSIGNMENT
from app.agent.writeback.rule_ranks import RANK_WORDS
from app.agent.writeback.value_authorization import as_number
from app.agent.writeback.target_semantics import _label_matches

UNREAD = "요청에 있는"  # a reading that left out a named condition: asked once more with the name


def unread_names(instruction, readings):
    """'‘사원’(직급)' for each source value named in the request's subject that no (table, rule) uses."""
    subject = ASSIGNMENT.split(instruction, maxsplit=1)[0]
    used = {str(item.value) for _, rule in readings for item in (*rule.filters, *rule.value_row_filters)
            if isinstance(item.value, str)}
    named = {*used, *(str(getattr(rule, name) or "") for _, rule in readings
                      for name in ("target_column_id", "value_column_id", "find_text"))}
    for _, rule in readings:
        named |= {str(item.column_id) for item in rule.filters}
    for name in sorted(named, key=len, reverse=True):
        if len(name) >= 2:
            subject = re.sub(re.escape(name), " ", subject, flags=re.I)
    missing = {}
    for table, _ in readings:
        headers = {column.id: column.display_header for column in table.columns}
        for row in table.rows:
            for column, value in row.values.items():
                if isinstance(value, str) and value.strip() and value not in missing and _label_matches(value, subject):
                    missing[value] = headers.get(column, column)
    return [f"‘{value}’({header})" for value, header in missing.items()]


def named_value(value, instruction):
    """The request names this source value: the text, the number, or the date as '11월 3일' / 2024-11-03."""
    when = value if isinstance(value, datetime) else _date(value)
    if when is not None:
        return bool(re.search(rf"(?<!\d){when.month}\s*월\s*{when.day}\s*일|{when.date().isoformat()}|"
                              rf"(?<![\d.]){when.month}\s*[/.]\s*{when.day}(?![\d])", instruction))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return as_number(value) in {as_number(token) for token in re.findall(r"\d[\d,]*(?:\.\d+)?", instruction)}
    return isinstance(value, str) and _label_matches(value, instruction)


def guessed_rows(rule, filters, table, instruction):
    """'예산이 가장 큰' read as 프로젝트명 = PRJ-L plus a rank: an equals pick of one row the request never names."""
    if not (rule.rank or rule.average_filters or RANK_WORDS.search(instruction)):
        return []
    return [str(item.value) for item in filters if item.operator == "equals" and not named_value(item.value, instruction)
            and sum(same_value(row.values.get(item.column_id), item.value) for row in table.rows) == 1]


def _date(value):
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) and re.match(r"\d{4}-\d{2}-\d{2}", value) else None
    except ValueError:
        return None
