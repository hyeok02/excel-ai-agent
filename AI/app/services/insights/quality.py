import math
from datetime import datetime

from app.services.insights.fact_trends import is_identity_row
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from app.services.insights.source_records import source_record_insights


def ensure_business_report(
    report: WorkbookInsightReport, context: dict[str, object]
) -> WorkbookInsightReport:
    # Generation is not validation: do not judge truth by numeric density or addresses.
    # A nonempty draft is left for the separate evidence validator to evaluate.
    if report.insights:
        return report
    return build_source_report(context)


def build_source_report(
    context: dict[str, object], max_insights: int = 5
) -> WorkbookInsightReport:
    """Build a literal source-only draft; callers must still validate its evidence."""
    limit = max(0, min(max_insights, 5))
    changes = [change for change in metric_changes(context) if _complete_change(change)]
    # Identity rows are separate evidence: do not attach their subject to trend cells.
    insights = [_change_insight(None, change) for change in changes[:limit]]
    if not insights:
        insights = source_record_insights(context, limit)
    return WorkbookInsightReport(
        overview=(
            " ".join(insight.fact for insight in insights[:2])
            if insights
            else "분석 입력에서 직접 확인할 수 있는 내용이 부족합니다."
        ),
        insights=insights,
        limitations=[
            "분석 입력에서 선별된 원본 값만 정리했으며, 원인이나 파일 밖의 비교는 추정하지 않았습니다."
        ],
    )


def _complete_change(change: dict[str, object]) -> bool:
    if not all(change.get(key) for key in ("metric", "earliest_period", "latest_period", "evidence")):
        return False
    for key in ("earliest_value", "latest_value", "change", "change_rate_percent"):
        value = change.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return False
    return isinstance(change["evidence"], list) and all(
        isinstance(item, str) and item.strip() for item in change["evidence"]
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
            if is_identity_row(values):
                return str(values[-1]["value"]).strip()
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
        impact=None,
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
