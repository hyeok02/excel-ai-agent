"""질문이 이름을 댄 항목 하나의 변화를 고른다.

"가장 많이 감소한 부서는?"은 1위를 집으면 되지만 "서비스 부서 인원 알려줘"는
이름을 댄 항목을 찾아야 한다. 머리글이 'Services'인데 질문은 '서비스'라
글자로는 겹치지 않으므로, 모델이 짚어 준 대상 이름을 함께 본다.
"""
from app.services.insights.display.glossary import readable

MIN_TERM = 2
COUNT_WORDS = ("몇", "개수", "건수", "how many", "count")
# 시계열 표는 점검표 모양이 아니라 개수 빌더가 붙지 않는다. 비교가 모아 둔
# 지표 수가 곧 부서 수다.
GROUP_NAMES = {"department": "부서", "role": "직무"}


def comparison_payload(comparison: object, question: str, intent) -> dict[str, object]:
    """비교에서 나오는 값과, 답변 쪽이 어떤 질문인지 알기 위해 필요한 표시."""
    targets = tuple(getattr(intent, "targets", ()) or ())
    return {
        "time_series_comparison": comparison,
        "named_metric_change": build_metric_change(comparison, question, targets),
        "metric_count": build_metric_count(comparison, question),
        "answer_kind": getattr(intent, "kind", ""),
    }


def build_metric_count(comparison: object, question: str) -> dict[str, object] | None:
    """'부서가 총 몇 개야?' — 비교가 모아 둔 지표를 센다."""
    if not isinstance(comparison, dict):
        return None
    group = GROUP_NAMES.get(str(comparison.get("metric_group")))
    normalized = question.casefold()
    if not group or group not in normalized:
        return None
    if not any(word in normalized for word in COUNT_WORDS):
        return None
    metrics = comparison.get("metrics")
    if not isinstance(metrics, list):
        return None
    references = [
        value
        for metric in metrics
        if isinstance(metric, dict) and _complete(metric)
        for value in metric.get("header_references") or ()
        if isinstance(value, str)
    ]
    counted = [
        metric for metric in metrics
        if isinstance(metric, dict) and _complete(metric)
    ]
    if not counted:
        return None
    return {
        "group": group,
        "count": len(counted),
        "names": [str(metric["header"]) for metric in counted],
        "references": list(dict.fromkeys(references)),
    }


def build_metric_change(
    comparison: object, question: str, targets: tuple[str, ...] = ()
) -> dict[str, object] | None:
    if not isinstance(comparison, dict):
        return None
    metrics = comparison.get("metrics")
    if not isinstance(metrics, list):
        return None
    ranked = [
        (score, metric)
        for metric in metrics
        if isinstance(metric, dict) and _complete(metric)
        if (score := _score(metric, question, targets))
    ]
    if not ranked:
        return None
    ranked.sort(key=lambda item: -item[0])
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        # 두 항목이 똑같이 걸리면 어느 쪽을 물었는지 알 수 없다.
        return None
    metric = ranked[0][1]
    return {
        "sheet_name": comparison.get("sheet_name"),
        "header": metric["header"],
        "header_references": [
            value for value in metric.get("header_references") or ()
            if isinstance(value, str)
        ],
        "start_value": metric["start_value"],
        "end_value": metric["end_value"],
        "change": metric["change"],
        "start_reference": metric["start_reference"],
        "end_reference": metric["end_reference"],
        # 기간을 말하는 문장이므로 기간이 적힌 칸도 근거로 든다.
        "period_references": [
            value
            for key in ("start_reference", "end_reference")
            if isinstance(value := comparison.get(key), str)
        ],
        "start_date": metric.get("start_date") or comparison.get("start_date"),
        "end_date": comparison.get("end_date"),
        "metric_group": comparison.get("metric_group"),
    }


def _complete(metric: dict) -> bool:
    required = (
        "header", "start_value", "end_value", "change",
        "start_reference", "end_reference",
    )
    return (
        all(metric.get(key) is not None for key in required)
        and isinstance(metric["header"], str)
        and bool(metric.get("header_references"))
    )


def _score(metric: dict, question: str, targets: tuple[str, ...]) -> int:
    """머리글의 낱말이 질문이나 모델이 짚은 대상에 그대로 나오는 글자 수."""
    header = readable(metric["header"]).casefold()
    asked = " ".join([question, *targets]).casefold()
    return sum(
        len(word)
        for word in header.replace("(", " ").replace(")", " ").replace(",", " ").split()
        if len(word) >= MIN_TERM and word in asked
    )
