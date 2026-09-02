# 도메인 교차 분석 회귀 fixture

`fixtures/semantic`이 표의 **생김새**를 다루는 반면, 이 디렉터리는 워크북의
**업무 종류**가 바뀌어도 판정이 유지되는지를 다룹니다.

분석 판정은 인사 워크북 하나를 보며 다듬어졌기 때문에, 구조 기반으로 바꾼
뒤에도 "도메인 중립"은 아직 주장일 뿐입니다. 여기 있는 워크북들은 그 주장을
검사하려고 각각 다른 전제를 하나씩 깨뜨리도록 만들어졌습니다.

## 구성

| fixture | 깨뜨리는 전제 |
| --- | --- |
| `cost_close_no_identity.xlsx` | 분석 대상 이름을 적어 둔 행이 항상 있다 |
| `equipment_snapshot_no_trend.xlsx` | 기간별 추이가 항상 존재한다 |
| `yield_report_english_only.xlsx` | 워크북에 한국어가 섞여 있다 |
| `energy_mixed_layout.xlsx` | 헤더는 한 번만 나오고 소계는 표 끝에 있다 |

워크북은 `build_fixtures.py`로 재생성합니다. 바이너리 `.xlsx`만 커밋하면
리뷰에서 내용을 확인할 수 없기 때문입니다.

```bash
cd AI && python -m tests.fixtures.analysis.build_fixtures
```

## 기대 결과에 무엇을 담는가

**LLM이 만든 문장을 고정하지 않습니다.** 모델이 조금만 달라져도 깨지고,
CI에서 API 비용이 들며, 결국 아무도 돌리지 않게 됩니다. 대신 그 문장을
**우리 검증기가 어떻게 처리하는지**를 고정합니다. 검증기는 결정론적이라
기대값이 흔들리지 않고, OpenAI 호출도 필요 없습니다.

| 항목 | 의미 |
| --- | --- |
| `subject` | 워크북에서 뽑은 분석 대상 이름. 근거가 없으면 `null`이 정답 |
| `numeric_changes` | 지표명·기간·값·변화율. 지표명은 워크북 헤더에서 온다 |
| `review_points` | 미리 적어 둔 impact 문장을 남기는가(`keep`) 버리는가(`drop`) |
| `questions` | 질문을 Agent에 넘기는가(`specific`) 되묻는가(`clarify`) |

`subject_reason`, `numeric_changes_reason`, 각 항목의 `reason`은 사람이 읽기
위한 설명이며 비교 대상이 아닙니다.

## 실행

```bash
cd AI
.venv/bin/python -m tests.run_analysis_regression
```

모든 fixture가 일치하면 종료 코드 `0`, 하나라도 어긋나면 `1`과 함께 어느
워크북의 무엇이 달랐는지 출력합니다. `pytest`로는
`tests/test_analysis_regression.py`가 같은 검사를 수행합니다.

## fixture를 추가할 때

1. `build_fixtures.py`에 워크북 생성 함수를 추가하고 `BUILDERS`에 등록합니다.
2. `manifest.json`에 `coverage` 태그로 **이 파일이 무엇을 깨뜨리는지** 적습니다.
3. `<workbook>.expected.json`에 기대값을 **손으로 먼저** 적습니다.
4. 그다음에 러너를 돌립니다.

3번과 4번의 순서를 바꾸면 안 됩니다. 코드를 돌려 나온 결과를 기대값으로
복사하면 현재 동작을 — 버그까지 포함해서 — 정답으로 승격시키게 됩니다.
처음 돌렸을 때 몇 개가 어긋나는 것이 정상이며, 그 어긋남이 바로 이 fixture를
만든 이유입니다.

`tests/test_analysis_fixture_invariants.py`의 불변식은 fixture를 추가하면
자동으로 함께 늘어나므로, 파일마다 손으로 적을 필요가 없습니다.
