"""Source names the request uses to pick rows that no rule reads.

"영업 부서 사원들 연봉을 300만원씩 올려줘" read as 부서 = 영업 alone would raise every 영업 salary; 사원 is a
직급 in the table and the request names it before the value. Such a reading is not applied: the request is
handed back with the name it left out. Only text values written before the value part are read.
"""
import re

from app.agent.writeback.natural_operations import ASSIGNMENT
from app.agent.writeback.target_semantics import _label_matches


def unread_names(instruction, readings):
    """'‘사원’(직급)' for each source value named in the request's subject that no (table, rule) uses."""
    subject = ASSIGNMENT.split(instruction, maxsplit=1)[0]
    used = {str(item.value) for _, rule in readings for item in rule.filters if isinstance(item.value, str)}
    named = {*used, *(str(getattr(rule, name) or "") for _, rule in readings
                      for name in ("target_column_id", "value_column_id"))}
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
