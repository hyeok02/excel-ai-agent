"""Boolean-plan instructions, shared by initial planning and bounded repair."""

BOOLEAN_FILTER_PROMPT = """
단일 표 조건은 filters에 원자 조건을 나열하고 filter_expression으로 논리구조를 지정할 수 있습니다.
filter_expression 노드: {operator: "predicate", filter_index: 0, children: []},
{operator: "and" 또는 "or", filter_index: null, children: [하위노드...]},
{operator: "not", filter_index: null, children: [하위노드 1개]}.
filters는 최대 8개, 모든 인덱스를 정확히 한 번 참조, 최대 깊이 5·노드 24개입니다.
filter_expression이 null이면 기존처럼 모든 filters는 AND입니다. OR를 AND로 바꾸지 마세요.
질문의 괄호·AND/OR/NOT 우선순위·제외 범위와 인용부호 안의 값을 보존하세요.
원본 열/값으로 확인할 수 있는 조건만 사용하고 누락 조건을 버리지 마세요.
예: (Region='North' OR Region='South') AND NOT Status='Closed'는
and(or(predicate(0), predicate(1)), not(predicate(2)))이며 실제 노드는 위 JSON 형식을 사용합니다.
숫자 % 임계값은 질문의 표시 숫자와 value_unit="percent"를 사용하세요.
표 연결(relational_query)의 filters는 여전히 AND만 지원하므로 OR/NOT 그룹을 평탄화하지 마세요.
"""
