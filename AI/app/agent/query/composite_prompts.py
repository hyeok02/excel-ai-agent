"""Bounded proposal only; original-clause coverage is checked independently."""

COMPOSITE_PROMPT = """
서로 다른 질문을 2~4개 함께 물으면 composite_query를 제안할 수 있습니다.
세미콜론, 줄바꿈, 물음표 또는 '비교하고, ... 알려줘'처럼 출력 동사 뒤 연결로
독립 질문을 나눕니다. 필터의 and/그리고, 인용된 값, 범위 A1:B10 안을 나누지 마세요.
composite_query.shared_prefix는 첫 문항 앞 '<공통 시트/조건>: ...'의 콜론 앞 원문만
그대로 복사합니다. 콜론으로 명시되지 않은 조건을 임의로 공통 조건으로 만들지 마세요.
parts 각 source_text는 순서대로 원문 부분 문자열을 그대로 복사하세요. 접속 동사의
'비교하고'는 첫 부분에 남기고, 그 뒤 쉼표/그리고만 구분자로 제외하세요.
부분마다 scope/kind/targets와 기존 tabular_query/relational_query/header_relation을
제안하며 계산 결과 숫자나 재작성 질문을 넣지 마세요. 공통 접두 조건은 모든 계획에 적용합니다.
어떤 조건·대상·문항도 버리면 안 됩니다. 계획이 없거나 애매한 부분도 parts에 남겨 kind=other로 둡니다.
'그중/위 결과/나머지' 등 이전 계산 결과에 의존하면 독립 질문으로 바꾸어 추측하지 마세요.
composite_query 사용 시 최상위의 tabular_query/relational_query/header_relation은 null입니다.
단일 집계의 복수 조건이나 '매출과 비용 합계'처럼 한 연산의 여러 열은 복합 질문으로 만들지 마세요.
"""
