"""Source-bound grouped statistics; no domain or workbook-specific rules."""
from app.agent.query.advanced_tabular_prompts import ADVANCED_TABULAR_PROMPT

GROUPED_TABULAR_PROMPT = """
단일 표에서 '부서별 매출 합계', '지역과 부서별 평균', '부서별 건수 상위 3개'처럼
그룹별 집계가 필요하면 tabular_query.group_by에 해당 원본 열 ID(최대 3개)를
넣으세요. 그룹 없는 질문은 group_by=[]입니다. 그룹은 필터 적용 후 전체 원본
행에서 형성되며, 그룹 순위는 행을 먼저 자른 결과가 아니라 전체 집계 결과입니다.
- 그룹별 수치 통계: operation=numeric_summary, column_ids에는 수치 열만,
  group_by에는 분류 열만 넣고 겹치지 않게 하세요. statistic은 요청한 연산입니다.
- 그룹별 행 건수: operation=row_count, column_ids=[], group_by=분류 열입니다.
- 그룹별 수치 상위/하위 N개: order_by는 column_ids 중 순위를 매길 수치 열,
  statistic은 sum/average/min/max 중 명시된 하나, descending과 limit=N입니다.
- 그룹별 건수 상위/하위 N개: order_by=null, descending과 limit=N입니다.
- 일반 행의 수치 상위/하위 N개: operation=row_list, group_by=[], order_by는
  순위 기준 열, column_ids에는 질문이 요청한 식별자/값을 모두 넣으세요.
임의 열 간 비율·기여도와 동점 전체 포함은 위 연산으로 대신하지 마세요.
그룹 수치 순위의 집계 연산이 모호하면 추정하지 말고 null로 두세요.
""" + ADVANCED_TABULAR_PROMPT
