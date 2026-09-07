"""Explain a focal transaction against its comparable-set median."""
import re

from app.services.insights.narrative_values import insight


def comparable_transaction_report(context):
    candidates = []
    for source_order, sheet in enumerate(context.get("sheets", [])):
        if not isinstance(sheet, dict):
            continue
        comparison = sheet.get("business_facts", {}).get("comparable_transactions")
        if not isinstance(comparison, dict):
            continue
        items = [_comparison_insight(comparison, metric)
                 for metric in comparison.get("metrics", [])]
        items = [item for item in items if item]
        if items:
            candidates.append((source_order, items, _overview(comparison)))
    if not candidates:
        return [], ""
    _, items, overview = min(candidates, key=lambda item: item[0])
    return items[:5], overview


def _comparison_insight(comparison, metric):
    subject = str(comparison.get("subject", "")).strip()
    peer_count = int(metric.get("peer_count", 0))
    valid_count = int(metric.get("valid_count", 0))
    if not subject or peer_count < 3 or valid_count < 3:
        return None
    current, middle = float(metric["subject_value"]), float(metric["median"])
    difference = current - middle
    rate = abs(float(metric["difference_percent"]))
    direction = "낮습니다" if difference < 0 else "높습니다"
    title_direction = "낮음" if difference < 0 else "높음"
    name = _metric_name(str(metric.get("kind", "")))
    coverage = (f"비교거래 {peer_count}건 중 값이 있는 {valid_count}건의"
                if valid_count < peer_count else f"비교거래 {peer_count}건의")
    fact = (
        f"{subject}의 {name}는 {_display(metric, current)}로, {coverage} 중앙값 "
        f"{_display(metric, middle)}보다 {_display(metric, abs(difference))}"
        f", 즉 {rate:.1f}% {direction}."
    )
    if metric.get("kind") == "ebitda_multiple":
        valuation = "저평가" if difference < 0 else "고평가"
        meaning = "낮다는" if difference < 0 else "높다는"
        fact += (
            f" 같은 EBITDA를 기준으로 지불한 거래가격이 {meaning} "
            f"뜻이지만, 비교 가능한 값이 {valid_count}건뿐이므로 {valuation}로 "
            "단정할 수 없습니다."
        )
    return insight(
        f"{_title_name(metric)}: 비교군 중앙값보다 {rate:.1f}% {title_direction}",
        fact, metric.get("evidence", []), "metric",
    )


def _metric_name(kind):
    return {
        "ebitda_multiple": "거래가치/EBITDA 배수",
        "transaction_value": "총 거래가치",
    }.get(kind, "거래 지표")


def _title_name(metric):
    return ("EBITDA 대비 거래가격" if metric.get("kind") == "ebitda_multiple"
            else _metric_name(str(metric.get("kind", ""))))


def _overview(comparison):
    metrics = {metric.get("kind"): metric for metric in comparison.get("metrics", [])}
    subject = str(comparison.get("subject", "")).strip()
    conclusions = []
    value = metrics.get("transaction_value")
    if value:
        direction = "작았습니다" if value["difference"] < 0 else "컸습니다"
        conclusions.append(
            f"총 거래가치는 비교군 중앙값보다 "
            f"{abs(value['difference_percent']):.1f}% {direction}."
        )
    multiple = metrics.get("ebitda_multiple")
    if multiple:
        direction = "낮았습니다" if multiple["difference"] < 0 else "높았습니다"
        conclusions.append(
            f"EBITDA 대비 거래가격은 비교군 중앙값보다 "
            f"{abs(multiple['difference_percent']):.1f}% {direction}."
        )
        if multiple["valid_count"] < multiple["peer_count"]:
            conclusions.append(
                f"다만 EBITDA 배수는 비교거래 {multiple['peer_count']}건 중 "
                f"{multiple['valid_count']}건만 확인돼 가격 수준을 단정하기 어렵습니다."
            )
    return f"{subject} 거래를 비교군과 대조했습니다. " + " ".join(conclusions)


def _display(metric, value):
    if metric.get("kind") == "ebitda_multiple":
        return f"{value:,.2f}배"
    label = str(metric.get("label", ""))
    if re.search(r"\$\s*M\b", label, re.I):
        return f"약 {value / 100:,.2f}억 달러(${value:,.1f}M)"
    return f"{value:,.1f}"
