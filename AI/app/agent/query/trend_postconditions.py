"""Never silently discard filtering/ranking of a calculated trajectory."""
import re

from app.agent.query.metric_request_coverage import _remove_source_phrase
from app.agent.query.trend_labels import trend_label_spellings

_DIRECTION = (r"(?:(?:증가|감소|상승|하락|반등|보합|개선|악화)"
              r"(?:한|하는|했던|하지\s*않(?:은|는))|늘어난|늘어나는|줄어든|줄어드는|오른|내린)\s+")
_SELECTION = r"(?:만(?![가-힣])|제외|빼고|골라|추려|선택|필터)"
_DIRECTIONAL_FILTER = re.compile(_DIRECTION + r"[^.!?;\n]{0,64}" + _SELECTION)
_ENGLISH_DIRECTION = r"(?:increasing|decreasing|rising|falling|rebounded|growing|shrinking|flat)"
_ENGLISH_SELECTION = r"(?:only|exclud\w*|filter\w*|keep|select)"
_ENGLISH_FILTER = re.compile(
    r"\b" + _ENGLISH_DIRECTION + r"\b[^.!?;\n]{0,64}\b" + _ENGLISH_SELECTION + r"\b|"
    r"\b" + _ENGLISH_SELECTION + r"\s+(?:(?:all|the|those|any)\s+)?" + _ENGLISH_DIRECTION + r"\b", re.I)
_RANKING = re.compile(
    r"상위|하위|순위|내림차순|오름차순|정렬|(?:높은|낮은|큰|작은|많은|적은)\s*순(?:서)?|"
    r"\b(?:top|bottom)\s*\d+|\b(?:rank(?:ing|ed)?|sort(?:ed)?|order\s+by)\b", re.I)


def trend_postcondition_error(question, observations, named_sheets=()):
    """Source-bound words are data; only unconsumed operation syntax is checked.

    Supported engines calculate every bound source group. Until a deterministic
    post-calculation predicate/order is applied, do not certify a subset/rank
    request by merely displaying all the groups with their computed values.
    """
    protected = set(named_sheets)
    for point in observations:
        protected.update(trend_label_spellings(point.label.value))
        protected.update(str(cell.value) for cell in (*point.entity_cells, *point.context_cells))
    operation = question.casefold()
    for label in sorted(protected, key=len, reverse=True):
        operation = _remove_source_phrase(operation, label)
    if _DIRECTIONAL_FILTER.search(operation) or _ENGLISH_FILTER.search(operation) or _RANKING.search(operation):
        return ("계산된 추이의 상승·하락 조건으로 대상을 고르거나 순위를 매기는 처리는 아직 확인할 수 없습니다. "
                "전체 대상의 추이를 먼저 질문해 주세요. 조건을 생략한 전체 결과에 근거 확인을 붙이지 않았습니다.")
    return None
