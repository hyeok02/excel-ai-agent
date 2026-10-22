"""Conservative, domain-neutral lexical gate for generated prose.

Values matching somewhere in a workbook do not establish the named subject or
metric. Content words must occur in the cited source; only grammar and generic
reporting vocabulary may be added. Uncertain paraphrases can fall back to source
quotations rather than displaying an invented claim. No LLM evidence prose is
ever added to the source vocabulary.
"""
import re

from app.services.insights.verification.validation_index import REFERENCE_PATTERN

WORDS = re.compile(r"[A-Za-z]+|[가-힣]+")
PARTICLES = ("입니다", "에서는", "에서", "으로", "까지", "부터", "보다", "처럼", "에는",
             "이며", "이고", "의", "은", "는", "이", "가", "을", "를", "에", "와", "과", "로", "도",
             "했습니다", "했으며", "했고", "합니다", "하며", "하고")
# Language glue only: never company names, industry terms, or domain synonyms.
# 비교·정도를 나타내는 말이 빠져 있으면 평범한 한국어 답변까지 근거 없음으로
# 막힌다. "가장 많이 줄었습니다"가 '가장' 하나 때문에 통째로 버려졌다.
# 단위어(명·원·퍼센트)는 여기 넣지 않는다. 단위는 의미를 담아서, 넣으면
# "열량은 750명입니다"처럼 단위를 바꿔치기한 주장이 통과한다.
REPORT_WORDS = set("""
값 지표 항목 대상 기준 시점 기간 현재 이전 최근 최신 시작 끝 처음 마지막
변화 증감 증가 감소 차이 비교 결과 구성 내용 현황 원본 근거 기록 정보 데이터
표 시트 셀 열 행 수식 범위 파일 워크북 합계 평균 최대 최소 전체 각각 동일
확인 검토 필요 추가 일부 모두 해당 이 그 및 또는 수 중 총 개 곳 년 월 일
분기 반기 연도 건 번 배 천 만 억 조 백만 이상 이하 초과 미만 약 대비 관련 대한 다른 같은
명확 정확 직접 실제 함께 먼저 원인 영향 여부 부족 없음 별도 기간별
있습니다 없습니다 입니다 입니다만 나타납니다 확인됩니다 기록됩니다
기록되어 표시되어 포함되어 구성되어 기록된 표시된 포함된 확인된
확인했습니다 증가했습니다 감소했습니다 달라졌습니다 변경됐습니다
줄었습니다 늘었습니다 유지됩니다 나타냅니다 보여줍니다 보여집니다
확인하세요 검토하세요 확인할 보입니다 됩니다 되어 있습니다 따른 따라
참조 참조합니다 포함됩니다 계산 계산된 연결 연결된 사용 사용하는 보존
최신값 이전값 변동 추이 증가한 감소한 기록됐습니다
해야 합니다 확인해야 판단해야 맞춰야 기준으로 규모 상태 경우 통합문서 경로
의존합니다 달라질
후속 산정 다시 should be reviewed against the recorded
가장 제일 많이 적게 크게 작게 높게 낮게 더 덜 상위 하위 순 순서 순으로
많은 적은 큰 작은 높은 낮은 적습니다 많습니다 큽니다 작습니다 컸습니다 작았습니다
폭 감소폭 증가폭 변동폭 증감폭 보면 살펴보면 나타났습니다 집계됐습니다 집계됩니다
줄어 줄어든 줄어들었습니다 늘어 늘어난 늘어났습니다 감소해 증가해 감소하여 증가하여
떨어졌습니다 올랐습니다 상승했습니다 하락했습니다 유지했습니다
""".split())
REPORT_WORDS.update(PARTICLES)


def _forms(word: str) -> set[str]:
    word = word.casefold()
    return {word, *(word[:-len(suffix)] for suffix in PARTICLES
                    if word.endswith(suffix) and len(word) > len(suffix))}


def grounded_claim(text: str, source_text: list[str], references: set[str]) -> bool:
    source_words = set()
    for source in [*source_text, *(ref.split("!")[0] for ref in references)]:
        for word in WORDS.findall(source):
            source_words.update(_forms(word))
    prose = REFERENCE_PATTERN.sub(" ", text)
    words = WORDS.findall(prose)
    if not words:
        return False
    grammar = set().union(*(_forms(word) for word in REPORT_WORDS))
    return all(_forms(word) & (source_words | grammar) for word in words)
