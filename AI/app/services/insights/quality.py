import re
from datetime import datetime

from app.services.insights.models import WorkbookInsight, WorkbookInsightReport


def ensure_business_report(
    report: WorkbookInsightReport, context: dict[str, object]
) -> WorkbookInsightReport:
    changes = _changes(context)
    if not changes or _is_concrete(report):
        return report
    target = _focus_target(context) or "분석 대상"
    current = _current_insight(target, context)
    insights = ([current] if current else []) + [
        _change_insight(target, change) for change in changes[:4]
    ]
    insights = insights[:5]
    overview = " ".join(insight.fact for insight in insights[:2])
    return WorkbookInsightReport(
        overview=overview,
        insights=insights,
        limitations=[
            "변화의 원인은 파일 안의 수치만으로 확인할 수 없어 단정하지 않았습니다."
        ],
    )


def _is_concrete(report: WorkbookInsightReport) -> bool:
    text = " ".join(
        [report.overview, *(insight.fact for insight in report.insights)]
    )
    evidence = [item for insight in report.insights for item in insight.evidence]
    return len(re.findall(r"\d[\d,.]*", text)) >= 2 and any(
        "!" in item and re.search(r"\d", item) for item in evidence
    )


def _changes(context: dict[str, object]) -> list[dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for sheet in context.get("sheets", []):
        facts = sheet.get("business_facts", {})
        for change in facts.get("numeric_changes", []):
            metric = str(change.get("metric"))
            previous = results.get(metric)
            if previous is None or str(change.get("earliest_period")) < str(
                previous.get("earliest_period")
            ):
                results[metric] = change
    return sorted(
        results.values(),
        key=lambda item: (
            _metric_priority(str(item.get("metric"))),
            abs(float(item.get("change_rate_percent", 0))),
        ),
        reverse=True,
    )


def _focus_target(context: dict[str, object]) -> str | None:
    for sheet in context.get("sheets", []):
        records = sheet.get("business_facts", {}).get("selected_records", [])
        for record in records:
            values = record.get("values", [])
            for index, value in enumerate(values[:-1]):
                label = str(value.get("value", "")).strip().casefold()
                if label.startswith("focus co") and "company" not in label:
                    return str(values[index + 1].get("value"))
    return None


def _current_insight(target: str, context: dict[str, object]) -> WorkbookInsight | None:
    for sheet in context.get("sheets", []):
        records = sheet.get("business_facts", {}).get("selected_records", [])
        for record in records:
            values = {str(item.get("label")): item.get("value") for item in record["values"]}
            headcount = values.get("Headcount (Latest)")
            tenure = values.get("Average Tenure (Latest)")
            if not isinstance(headcount, (int, float)):
                continue
            tenure_text = (
                f", 평균 근속은 {_display_number(tenure)}년" if isinstance(tenure, (int, float)) else ""
            )
            return WorkbookInsight(
                title=f"요약 표 최신 직원 수 {_display_number(headcount)}명",
                fact=f"{target}의 요약 표 기준 최신 직원 수는 {_display_number(headcount)}명{tenure_text}입니다.",
                cause=None,
                impact="인력 규모를 판단할 때 요약 표의 최신 기준값으로 사용할 수 있습니다.",
                category="summary",
                severity="info",
                evidence=[str(record["location"])],
                recommendation=None,
                confidence=0.98,
            )
    return None


def _change_insight(
    target: str, change: dict[str, object]
) -> WorkbookInsight:
    old = _display_number(change["earliest_value"])
    new = _display_number(change["latest_value"])
    delta = _display_number(abs(float(change["change"])))
    rate = abs(float(change["change_rate_percent"]))
    direction = "감소" if float(change["change"]) < 0 else "증가"
    metric = _metric_label(str(change["metric"]))
    return WorkbookInsight(
        title=f"{metric} {rate:g}% {direction}",
        fact=(
            f"{target}의 월별 추이에서 {metric} 지표는 {_period(change['earliest_period'])} {old}에서 "
            f"{_period(change['latest_period'])} {new}로 {delta}({rate:g}%) {direction}했습니다."
        ),
        cause=None,
        impact=(
            f"기간 시작점 수치를 최신 규모로 사용하면 {delta}의 차이가 발생하므로 "
            "최신 기간 값을 기준으로 비교해야 합니다."
        ),
        category="summary",
        severity="info",
        evidence=[str(item) for item in change["evidence"]],
        recommendation=None,
        confidence=0.99,
    )


def _display_number(value: object) -> str:
    number = float(value)
    return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"


def _period(value: object) -> str:
    try:
        return datetime.fromisoformat(str(value)).strftime("%Y년 %m월")
    except ValueError:
        return str(value)


def _metric_priority(metric: str) -> int:
    normalized = metric.casefold()
    return 3 if "total employee" in normalized or "headcount" in normalized else 1


def _metric_label(metric: str) -> str:
    return {
        "Total Employees": "전체 직원 수",
        "General & Administrative": "일반·관리 부문 인원",
        "Legal": "법무 부문 인원",
        "Analyst": "애널리스트 인원",
        "Finance": "재무 부문 인원",
    }.get(metric, metric)
