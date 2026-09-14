"""Explain a focal transaction against its comparable-set median."""
import re

from app.services.insights.narratives.narrative_values import insight


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
        topic=_title_name(metric),
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
    """
    비교 결과를 두 문장으로 줄인다.

    지표마다 문장을 따로 만들면 대상 이름과 "비슷한 거래"가 네 문장에 걸쳐 반복되어
    읽기 어려웠다. 결과는 한 문장에 모으고, 근거가 부족하면 그 사실만 덧붙인다.
    카드 제목과 같은 "중앙값"을 쓴다.
    """
    metrics = {metric.get("kind"): metric for metric in comparison.get("metrics", [])}
    value = metrics.get("transaction_value")
    multiple = metrics.get("ebitda_multiple")
    sentences = [sentence for sentence in (
        _result_sentence(value, multiple),
        _coverage_sentence(multiple),
    ) if sentence]
    return " ".join(sentences)


def _result_sentence(value, multiple):
    """두 지표가 모두 있으면 한 문장으로 잇는다."""
    if value and multiple:
        return (f"거래 가격은 비교 대상의 중앙값보다 {_gap(value)}고, "
                f"이익 대비 가격은 {_gap(multiple)}습니다.")
    if value:
        return f"거래 가격은 비교 대상의 중앙값보다 {_gap(value)}습니다."
    if multiple:
        return f"이익 대비 가격은 비교 대상의 중앙값보다 {_gap(multiple)}습니다."
    return ""


def _coverage_sentence(multiple):
    """이익 자료가 비교 거래 전부에서 확인되지 않으면 결론을 단정하지 않는다."""
    if not multiple or multiple["valid_count"] >= multiple["peer_count"]:
        return ""
    price = "저렴했다고" if multiple["difference"] < 0 else "비쌌다고"
    return (f"다만 이익 자료가 있는 거래가 {multiple['peer_count']}건 중 "
            f"{multiple['valid_count']}건뿐이라 실제로 {price} 단정하기는 어렵습니다.")


def _gap(metric):
    """"23.8% 낮" 처럼 어미를 붙여 쓸 수 있는 조각으로 돌려준다."""
    direction = "낮" if metric["difference"] < 0 else "높"
    return f"{abs(metric['difference_percent']):.1f}% {direction}"


def _display(metric, value):
    if metric.get("kind") == "ebitda_multiple":
        return f"{value:,.2f}배"
    label = str(metric.get("label", ""))
    if re.search(r"\$\s*M\b", label, re.I):
        return f"약 {value / 100:,.2f}억 달러(${value:,.1f}M)"
    return f"{value:,.1f}"
