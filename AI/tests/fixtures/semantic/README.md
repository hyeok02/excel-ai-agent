# Excel 의미 분석 fixture

이 디렉터리는 Excel 의미 분석 기능의 정답 기준을 관리합니다. 실제 분류 로직은 후속 작업에서 구현하며, 이 PR에서는 입력 워크북과 사람이 판정한 기대 결과만 고정합니다.

## 구성

| fixture | 검증 목적 |
| --- | --- |
| `semantic_simple_table.xlsx` | 제목, 단위, 단일 헤더, 데이터, 합계, 출처 구분 |
| `semantic_hierarchical_headers.xlsx` | 병합된 다단계 헤더, 별도 검토 기준, 시스템 캐시 시트 제외 |
| `semantic_mixed_regions.xlsx` | 입력, 계산, 의사결정 출력, 주의 문구, 사용안내 시트 구분 |

각 `.expected.json` 파일은 같은 이름의 워크북에 대한 기대 결과입니다. `manifest.json`은 fixture 목록과 각 파일이 담당하는 검증 범위를 정의합니다.

## 기대 결과 규칙

### 시트 판단

- `analyze`: 핵심 업무 데이터로 분석과 인사이트 생성에 사용
- `metadata_only`: 사용법이나 설명처럼 답변의 배경 정보로만 사용
- `exclude`: 애드인 캐시처럼 사용자 분석에서 완전히 제외

### 영역 역할

- `title`: 워크북 또는 표의 제목
- `unit`: 숫자 해석에 필요한 단위
- `header`: 열 또는 계층형 헤더
- `data`: 관측값이나 업무 데이터
- `total`: 합계·소계 같은 집계 결과
- `source_note`: 출처와 기준일
- `rule_note`: 판단 또는 검토 기준
- `input`: 사용자가 변경하는 가정값
- `calculation`: 수식으로 계산되는 중간 결과
- `output`: 의사결정에 직접 사용하는 최종 결과
- `instruction`: 사용 방법
- `warning`: 결과 해석 시 주의 사항
- `system_cache`: 업무 의미가 없는 시스템 캐시

### 영역 판단

- `analyze`: 계산·비교·요약 대상으로 사용
- `context`: 값 자체를 집계하지 않고 해석 문맥으로 사용
- `exclude`: 프롬프트와 인사이트 생성에서 제외

`answer_cells`는 질문의 직접 답을 제공하는 셀이고, `supporting_cells`는 답의 계산이나 해석 근거로 함께 표시할 셀입니다.

## 회귀 테스트 실행

의미 분석기가 생성한 결과를 `<workbook stem>.actual.json` 이름으로 한 디렉터리에 저장한 뒤 아래 명령으로 기대 결과와 비교합니다.

```bash
cd AI
.venv/bin/python -m tests.run_semantic_regression --actual-dir <결과 디렉터리>
```

actual JSON은 다음 필드를 사용합니다. 기대 결과 JSON의 `reason`, `expected_formula_count`, `reference_answers`처럼 비교 대상이 아닌 필드는 포함하지 않아도 됩니다.

```json
{
  "workbook": "semantic_simple_table.xlsx",
  "sheets": [
    {
      "name": "월별 매출",
      "decision": "analyze",
      "sheet_role": "business_data",
      "regions": [
        {
          "range": "A1:D1",
          "role": "title",
          "decision": "context",
          "units": []
        }
      ]
    }
  ]
}
```

모든 fixture가 일치하면 종료 코드 `0`, 하나라도 오분류되거나 실행 중 예외가 발생하면 종료 코드 `1`을 반환합니다. 실패 결과에는 누락·추가된 시트와 영역, 역할·처리 방식·단위 불일치 위치가 함께 출력됩니다.
