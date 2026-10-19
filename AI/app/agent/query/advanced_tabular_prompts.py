"""Compose supported aggregate stages using source IDs, never generated results."""

ADVANCED_TABULAR_PROMPT = """
추가 공통 연산도 파일/열 이름을 외우지 말고 실제 tables 카탈로그 ID로 지정하세요.
계산 순서는 원본 filters → 전체 그룹 집계/중복 제외 → 비중 분모 확정 → having → 정렬/표시입니다.
- '항목별 금액 합계가 1억 넘는 항목': numeric_summary+sum+group_by,
  원본 행 조건은 filters, 계산된 합계 조건은 having에 지정합니다. value는 원본 저장 단위입니다.
  1억=100000000이지만 원본 열이 '금액(백만원)'이면 1억원 조건의 value는 100입니다.
  원본 통화/배율이 불명확하거나 환율·복합 표시 형식 변환이 필요하면 추측하지 말고 null로 두세요.
  '넘는/초과'는 greater_than, '이상'은 greater_than_or_equal입니다. 둘을 혼동하지 마세요.
  having에는 column_id=집계 수치 열, target=aggregate, operator, value, value_unit을 적습니다.
  행 건수/중복 제외 건수의 having.column_id는 null입니다. having은 AND 조건입니다.
- '항목별 전체 금액 비중': numeric_summary+sum+단일 column_ids+group_by+share_of_total=true.
  행 건수 비중은 row_count입니다. 분모는 같은 원본 filters를 통과한 전체입니다.
  상위 N개나 having을 적용한 뒤 남은 그룹만으로 분모를 다시 계산하지 않습니다.
  비중 조건은 having.target=share,column_id=null,value_unit=percent이며 10%는 value=10입니다.
  '전체'가 별도 모집단/시트/원본 필터 제외를 뜻하면 이 기능으로 대신하지 말고 null로 두세요.
- '중복 제외한 항목 수': operation=distinct_count, kind=row_count 또는 aggregation,
  column_ids=중복을 판단할 원본 열(최대 3개), statistic=all입니다. 여러 열은 조합의 고유 건수입니다.
  전체 고유 건수는 group_by=[], 분류별 고유 건수는 group_by를 넣으세요.
  빈칸/공백/불완전 조합은 제외하되 수식의 알 수 없는 결과는 빈칸으로 간주하지 않습니다.
  중복 제외 건수 순위는 order_by=null,limit=N입니다. 중복 제외 비중은 지원하지 않습니다.
- '각 분류에서 금액 상위 3개씩': operation=row_list, group_by=분류 열,
  order_by=원본 수치 열, descending, per_group_limit=3, limit=null입니다.
  그룹 합계 순위와 다릅니다. column_ids는 요청한 이름/ID/값을 포함합니다.
  '상위 3명' 등 개체 순위라면 identity_column_ids에도 원본 이름/ID 열(최대 3개)을 넣고
  column_ids에 포함하세요. 코드는 각 그룹 전체에서 한 개체당 한 행인지 확인합니다.
  동일 개체의 여러 기록을 먼저 합산해야 하면 이 원본 행 순위로 대신하지 마세요.
having/share_of_total/per_group_limit은 질문에 없는 경우 각각 []/false/null입니다.
복수 단계 중 지원하지 않는 단계가 있으면 생략한 계획으로 답하지 말고 null로 두세요.
"""
