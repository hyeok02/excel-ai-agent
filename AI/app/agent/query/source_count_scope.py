"""A deterministic count shortcut cannot silently discard a remaining scope."""
import re

from app.agent.query.metric_request_coverage import _remove_source_phrase
from app.agent.query.search_terms import KOREAN_SUFFIXES

_GRAMMAR = set((
    "시트 표 파일 원본 전체 총 행 기록 요청 거래 장비 항목 자료 데이터 건수 개수 수 건 개 대 곳 "
    "조건 해당 몇 인 이 가 의 은 는 을 를 에 에서 아닌 제외 포함 포함된 빈칸 공백 "
    "how many count number of records record rows row items item transactions transaction "
    "requests request in on from the sheet table file is are not where equals equal to "
    "contains include including excluding except blank empty null please tell me show all total"
).split())


def count_scope_covered(question, plan, table):
    text = question.casefold()
    sources = [table.sheet_name, *(column.header for column in table.columns),
               *(str(item.value) for item in plan.filters if item.value is not None)]
    for source in sorted(sources, key=len, reverse=True):
        text = _remove_source_phrase(text, source)
        text = re.sub(r"(?<![a-z0-9_가-힣])" + re.escape(source)
                      + r"(?=(?:인|이고|이며)(?:\s|$))", " ", text, flags=re.I)
    for token in re.findall(r"[a-z0-9_가-힣]+", text):
        if re.fullmatch(r"(?:몇|건|개|대|곳)(?:이야|야|인가요|인지|입니까)?", token):
            continue
        if token.startswith(("알려", "보여", "말해")) or token in {"있어", "있나요"}:
            continue
        forms = {token, *(token[:-len(suffix)] for suffix in KOREAN_SUFFIXES
                           if suffix and token.endswith(suffix) and len(token) > len(suffix))}
        if not forms & _GRAMMAR:
            return False
    return True
