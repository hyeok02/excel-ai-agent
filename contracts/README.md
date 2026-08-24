# 공통 분석 계약

AI, Spring Boot, Frontend가 주고받는 분석 데이터의 wire value를 관리합니다. 의미 역할의 기준 파일은 `semantic-classification.schema.json`이며 모든 역할은 소문자 문자열로 전달합니다.

## 의미 역할

| 역할 | 적용 기준 |
| --- | --- |
| `title` | 시트나 표 전체의 제목 |
| `description` | 데이터의 목적이나 내용을 설명하는 문장 |
| `unit` | 통화·비율·인원 등 수치 단위 |
| `header` | 행·열 또는 계층형 헤더 |
| `data` | 분석 대상 원본 값 |
| `formula` | 개별 수식 셀 |
| `note` | 일반 주석이나 참고 문장 |
| `total` | 합계·소계·집계 결과 |
| `input` | 사용자가 변경하는 가정이나 입력 영역 |
| `calculation` | 수식이 중심인 중간 계산 영역 |
| `output` | 의사결정에 직접 사용하는 최종 결과 |
| `instruction` | 워크북 사용 방법 |
| `warning` | 해석 또는 변경 시 주의 사항 |
| `source_note` | 데이터 출처와 기준일 |
| `rule_note` | 판단 기준과 검토 규칙 |
| `system_cache` | 애드인·도구가 만든 시스템 캐시 |
| `ignore` | 의미 분석에서 제외하기로 확정된 영역 |
| `unknown` | 아직 역할을 판정하지 못한 영역 |

## 분류 결과

`SemanticClassification`은 다음 정보를 포함합니다.

- `role`: 의미 역할
- `confidence`: 0~1 범위의 판정 신뢰도
- `reasons`: 판정 규칙 코드, 사용자용 설명, 근거 셀 목록

분석 포함 여부와 제외 사유는 역할과 다른 정책 결과이므로 Phase 1-3에서 별도 필드로 추가합니다. 예를 들어 `note` 역할은 분석 문맥에 포함될 수도 있고 제외될 수도 있습니다.
