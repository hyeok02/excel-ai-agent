import re
from datetime import datetime

from app.services.insights.fact_trends import is_plain_text
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport


def ensure_business_report(
    report: WorkbookInsightReport, context: dict[str, object]
) -> WorkbookInsightReport:
    changes = metric_changes(context)
    if not changes or _is_concrete(report):
        return report
    subject = subject_name(context)
    insights = [_change_insight(subject, change) for change in changes[:5]]
    return WorkbookInsightReport(
        overview=" ".join(insight.fact for insight in insights[:2]),
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


def metric_changes(context: dict[str, object]) -> list[dict[str, object]]:
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
        key=lambda item: abs(float(item.get("change_rate_percent", 0))),
        reverse=True,
    )


def subject_name(context: dict[str, object]) -> str | None:
    """'이름표 | 값' 두 칸으로 적힌 분석 대상 이름을 행의 모양으로만 찾는다.

    특정 워크북의 머리글 문구에 의존하지 않으므로 업종이 다른 파일에서도
    같은 규칙으로 동작한다. 해당하는 행이 없으면 대상을 붙이지 않는다.
    """
    for sheet in context.get("sheets", []):
        records = sheet.get("business_facts", {}).get("selected_records", [])
        for record in records:
            values = record.get("values", [])
            if len(values) != 2:
                continue
            label, name = (item.get("value") for item in values)
            if is_plain_text(label) and is_plain_text(name):
                return str(name).strip()
    return None


def _change_insight(
    subject: str | None, change: dict[str, object]
) -> WorkbookInsight:
    old = _display_number(change["earliest_value"])
    new = _display_number(change["latest_value"])
    delta = _display_number(abs(float(change["change"])))
    rate = abs(float(change["change_rate_percent"]))
    direction = "감소" if float(change["change"]) < 0 else "증가"
    metric = str(change["metric"])
    owner = f"{subject}의 " if subject else ""
    return WorkbookInsight(
        title=f"{metric} {rate:g}% {direction}",
        fact=(
            f"{owner}{metric} 지표는 {_period(change['earliest_period'])} {old}에서 "
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
