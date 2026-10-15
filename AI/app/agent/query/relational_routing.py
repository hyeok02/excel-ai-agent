"""A cross-table request must never silently degrade to a one-table answer."""
import re

from app.agent.query.models import QuestionAnswer
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_scope import explicit_ranges

_JOIN = re.compile(r"결합|조인|연결\s*(?:해서|하여|한|해|하[고여])|매칭|\b(?:join|merge|match)\b", re.I)


def missing_relational_plan_answer(question, summary, intent=None):
    if getattr(intent, "relational_query", None) is not None or not _JOIN.search(question):
        return None
    tables = build_query_tables(summary)
    text = " ".join(question.casefold().split())
    selected = set()
    for table in tables:
        same_sheet = [other for other in tables if other.sheet_name == table.sheet_name]
        named_sheet = " ".join(table.sheet_name.casefold().split()) in text
        named_caption = any(" ".join(value.casefold().split()) in text
                            for _, value in table.context if isinstance(value, str) and len(value.strip()) >= 4)
        named_range = any(sheet == table.sheet_name and reference == table.reference
                          for sheet, reference in explicit_ranges(question))
        if (named_sheet and len(same_sheet) == 1) or named_caption or named_range:
            selected.add(table.id)
    if len(selected) < 2:
        return None
    scopes = ", ".join(sorted(selected))
    message = (f"두 표 이상을 연결하는 질문이지만 연결 키와 대상 행 범위를 확정하지 못했습니다. "
               f"한 표의 값으로 대신 답하지 않았습니다. 대상: {scopes}. "
               "‘왼쪽 표의 어떤 열 = 오른쪽 표의 어떤 열’인지와 전체 행 또는 일치하는 행만 사용할지 지정해 주세요.")
    return QuestionAnswer(question=question, answer=message, status="insufficient_evidence", confidence=0,
                          selected_tools=["relational_query"], evidence=[], limitations=[message])
