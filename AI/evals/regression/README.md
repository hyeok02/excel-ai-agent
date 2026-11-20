# Q&A 회귀 배터리 (녹화·재생)

질문 처리 코드를 바꾸기 전과 후의 답변을 비교해, 이전에 답하던 질문이 막히지 않았는지 확인한다.
모델 응답은 한 번 녹화한 뒤 재생하므로, 비교할 때마다 API 비용이 들지 않는다.

```
# 1) 녹화 (모델 호출 비용 발생, 저렴한 모델 권장)
OPENAI_INTENT_MODEL=gpt-4.1-mini OPENAI_QA_MODEL=gpt-4.1-mini \
python -m evals.regression.battery record --data <공개 샘플 폴더> --tape tape.json --out before.jsonl

# 2) 코드 수정 후 재생 (비용 없음)
python -m evals.regression.battery replay --data <공개 샘플 폴더> --tape tape.json --out after.jsonl

# 3) 비교: 이전에 답하던 질문이 답하지 못하게 되면 종료 코드 1
python -m evals.regression.compare before.jsonl after.jsonl
```

- `baseline_answers.jsonl`, `baseline_tape.json`: 현재 코드로 녹화한 기준 답변(159개)과 그 모델 응답
  (gpt-4.1-mini). 코드를 고친 뒤 `replay --tape baseline_tape.json`으로 돌려 `baseline_answers.jsonl`과 비교한다.
- `questions.tsv`: 파일 이름과 질문. `data/`의 두 파일은 테스트용으로 만든 예시이고, 나머지 9개는 공개 샘플
  파일(EIA, EPA, NHS, ONS, 영국 온실가스, 식품 판매·보험 예시)을 `--data` 폴더로 지정한다.
- 재생 중 녹화에 없는 모델 요청은 오류 응답으로 처리하고 `not recorded`로 보고한다. 모델에 보내는
  질문 프롬프트가 바뀌는 수정은 다시 녹화해야 한다.
- 녹화와 재생이 같은 요청을 만들도록, 질문마다 라벨 번역을 비운 상태에서 시작하고 `PYTHONHASHSEED=0`으로
  실행한다(앞에 어떤 질문이 실행됐는지, 실행을 몇 번에 나눴는지에 따라 요청이 달라지지 않게).
- 녹화 중에도 테이프에 이미 있는 요청은 다시 호출하지 않고 테이프 응답을 쓴다. 같은 파일의 질문들은 같은
  라벨 번역 요청을 보내는데, 모델이 매번 조금씩 다르게 번역하므로 다시 부르면 먼저 녹화한 질문의 프롬프트가 어긋난다.
  일부 질문만 다시 녹화할 때도 이 덕분에 나머지 질문의 재생이 깨지지 않는다.
- 긴 실행은 `--append --deadline 초`로 나눠 돌릴 수 있다(이미 결과가 있는 질문은 건너뛰고, 질문마다 테이프 저장).
