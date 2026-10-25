"""Explain a focal deal against its comparable set without overclaiming.

Only a multiple (price per unit of earnings) says whether a price was high or
low, and only when at least half of the peers report it. Thinner multiples are
named as excluded. The deal amount is described as size, never as price.
"""
import re

from app.services.insights.narratives.comparable_wording import (
    NUMERATOR_NAMES, announced, basis_name, coverage, display, gap,
    normalized, short_amount, size_name, thin_note, usable,
)
from app.services.insights.narratives.narrative_values import insight


def comparable_transaction_report(context):
    candidates = []
    for source_order, sheet in enumerate(context.get("sheets", [])):
        if not isinstance(sheet, dict):
            continue
        comparison = sheet.get("business_facts", {}).get("comparable_transactions")
        if not isinstance(comparison, dict) or not str(comparison.get("subject", "")).strip():
            continue
        items = _cards(comparison)
        if items:
            candidates.append((source_order, items, _overview(comparison)))
    if not candidates:
        return [], ""
    _, items, overview = min(candidates, key=lambda item: item[0])
    return items[:5], overview


def comparison_lead_sentence(subject, comparison):
    """Whose deal, when, how large, against how many peers."""
    buyer = comparison.get("buyer")
    deal = f"{buyer}의 {subject} 인수 거래" if buyer else f"{subject} 인수 거래"
    _, _, size = _split(comparison)
    details = [part for part in (
        announced(comparison.get("announced")) if comparison.get("announced") else "",
        f"{size_name(size)} {short_amount(size['label'], size['subject_value'])}" if size else "",
    ) if part]
    if details:
        deal += f"({', '.join(details)})"
    peers = comparison.get("peer_count") or next(
        (item.get("peer_count") for item in comparison.get("metrics", []) if item.get("peer_count")), 0)
    against = f"비교 거래 {peers}건과" if peers else "비교 거래들과"
    return f"이 파일은 {deal}를 {against} 비교한 자료입니다."


def _split(comparison):
    metrics = [normalized(item) for item in comparison.get("metrics", []) if isinstance(item, dict)]
    multiples = [item for item in metrics if item["unit"] == "multiple" and not item["is_size"]]
    ranked = sorted((item for item in multiples if usable(item)),
                    key=lambda item: (-int(item["valid_count"]), bool(item.get("derived"))))
    thin = [item for item in multiples if not usable(item)]
    size = next((item for item in metrics if item["is_size"]
                 and int(item.get("valid_count", 0)) >= 3), None)
    return ranked, thin, size


def _cards(comparison):
    subject = str(comparison["subject"]).strip()
    ranked, thin, size = _split(comparison)
    cards = [_multiple_card(subject, metric, thin if index == 0 else [])
             for index, metric in enumerate(ranked[:2])]
    if size:
        cards.append(_size_card(subject, size))
    return cards


def _multiple_card(subject, metric, thin):
    name, lower = basis_name(metric), float(metric["difference"]) < 0
    fact = (f"{subject}의 {name} 대비 인수가격은 {display(metric, metric['subject_value'])}로, "
            f"{coverage(metric)} 중앙값 {display(metric, metric['median'])}보다 "
            f"{gap(metric)} {'낮습니다' if lower else '높습니다'}.")
    if metric.get("derived"):
        top, bottom = metric["numerator"], metric["denominator"]
        fact += (" 원본에 있는 배수가 아니라 계산한 값입니다: "
                 f"{_plain(top['label'])} {short_amount(top['label'], top['value'])} ÷ "
                 f"{_plain(bottom['label'])} {short_amount(bottom['label'], bottom['value'])}.")
    if note := thin_note(thin, metric["peer_count"]):
        fact += f" {note} 비교에 쓰지 않았습니다."
    return insight(f"{name} 대비 인수가격: 비교군 중앙값보다 {gap(metric)} {'낮음' if lower else '높음'}",
                   fact, metric.get("evidence", []), "metric", topic=f"{name} 대비 인수가격")


def _plain(label):
    return re.sub(r"\s*\([^)]*\)", "", str(label)).strip()


def _size_card(subject, metric):
    smaller = float(metric["difference"]) < 0
    fact = (f"{subject}의 {size_name(metric)}는 {display(metric, metric['subject_value'])}로, "
            f"{coverage(metric)} 중앙값 {display(metric, metric['median'])}보다 "
            f"{gap(metric)} {'작습니다' if smaller else '큽니다'}. "
            "거래 규모를 비교한 것이며, 인수가격이 싸거나 비쌌다는 뜻은 아닙니다.")
    return insight(f"거래 규모: 비교군 중앙값보다 {gap(metric)} {'작음' if smaller else '큼'}",
                   fact, metric.get("evidence", []), "metric", topic="거래 규모")


def _overview(comparison):
    ranked, thin, size = _split(comparison)
    peers = comparison.get("peer_count") or next(
        (item["peer_count"] for item in (*ranked, *thin) if item.get("peer_count")), 0)
    note = thin_note(thin, peers)
    if not ranked:
        sentences = [f"{thin_note(thin, peers, '가')} 가격 수준은 판단할 수 없습니다." if thin
                     else "가격 수준을 비교할 배수 열이 없습니다."]
        if size:
            sentences.append(f"비교할 수 있는 것은 거래 규모뿐이며, 비교 거래 중앙값보다 "
                             f"{gap(size)} {'작습니다' if size['difference'] < 0 else '큽니다'}.")
        return " ".join(sentences)
    best, lower = ranked[0], ranked[0]["difference"] < 0
    how = (f"({NUMERATOR_NAMES.get(best.get('numerator_role'), '인수가격')} ÷ {basis_name(best)} 계산값)"
           if best.get("derived") else "")
    sentences = [f"{basis_name(best)} 대비 인수가격{how}은 비교 거래 중앙값보다 "
                 f"{gap(best)} {'낮습니다' if lower else '높습니다'}."]
    if caveat := _industry_caveat(comparison.get("industry"), peers, lower):
        sentences.append(caveat)
    if note:
        sentences.append(f"{note} 비교에서 뺐습니다.")
    return " ".join(sentences)


def _industry_caveat(industry, peers, lower):
    """Only a fully observed peer industry list can say "none is the same"."""
    if not isinstance(industry, dict):
        return ""
    counts = [(str(name), int(count)) for name, count in industry.get("peers", [])]
    if sum(count for _, count in counts) != peers or any(name == industry["subject"] for name, _ in counts):
        return ""
    top, count = counts[0]
    verdict = "싸게" if lower else "비싸게"
    return (f"다만 비교 거래는 {top} {count}건 등이고 대상과 같은 업종({industry['subject']})은 "
            f"없어, {verdict} 인수했다고 단정하기는 어렵습니다.")
