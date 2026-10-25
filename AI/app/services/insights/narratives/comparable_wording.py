"""Shared wording for comparable-deal metrics: names, values and coverage."""
import re
from datetime import date

BASIS_NAMES = {"net_income": "순이익", "ebitda": "EBITDA", "ebit": "EBIT",
               "revenue": "매출", "book": "장부가"}
NUMERATOR_NAMES = {"equity": "지분가치", "enterprise": "기업가치", "size": "거래가치"}


def normalized(metric):
    """Accept older fact shapes (ebitda_multiple / transaction_value) too."""
    kind = metric.get("kind")
    unit = metric.get("unit") or ("multiple" if kind == "ebitda_multiple" else "amount")
    basis = metric.get("basis") or ("ebitda" if kind == "ebitda_multiple" else None)
    return {**metric, "unit": unit, "basis": basis,
            "is_size": kind in {"size", "transaction_value"}}


def usable(metric):
    """A price conclusion needs values for at least half of the peers."""
    valid, peers = int(metric.get("valid_count", 0)), int(metric.get("peer_count", 0))
    return valid >= 3 and valid * 2 >= peers


def basis_name(metric):
    basis = str(metric.get("basis") or "")
    return BASIS_NAMES.get(basis, basis or "이익")


def size_name(metric):
    label = str(metric.get("label", ""))
    if re.search(r"[가-힣]", label):
        return re.sub(r"\s*\([^)]*\)", "", label).strip()
    return "총 거래가치" if "total" in label.casefold() else "거래가치"


def display(metric, value):
    if metric.get("unit") == "multiple":
        return f"{value:,.2f}배"
    return amount(str(metric.get("label", "")), value)


def amount(label, value):
    if re.search(r"\$\s*M\b", label, re.I):
        return f"약 {value / 100:,.2f}억 달러(${value:,.1f}M)"
    return short_amount(label, value)


def short_amount(label, value):
    if re.search(r"\$\s*M\b", label, re.I):
        return f"${value:,.1f}M"
    unit = re.search(r"\(([^()]{1,6})\)\s*$", str(label).strip())
    return f"{value:,.1f}{unit.group(1).strip() if unit else ''}"


def coverage(metric):
    valid, peers = int(metric["valid_count"]), int(metric["peer_count"])
    return f"비교 거래 {peers}건 중 값이 있는 {valid}건의" if valid < peers else f"비교 거래 {peers}건의"


def gap(metric):
    return f"{abs(float(metric['difference_percent'])):.1f}%"


def thin_note(thin, peers, particle="는"):
    """Name every price multiple left out and why, in one clause."""
    if not thin:
        return ""
    names = "·".join(dict.fromkeys(basis_name(item) for item in thin))
    counts = {int(item["valid_count"]) for item in thin}
    count = f"{counts.pop()}건만" if len(counts) == 1 else f"많아야 {max(item['valid_count'] for item in thin)}건만"
    return f"{names} 기준 배수{particle} {peers}건 중 {count} 값이 있어"


def announced(value):
    try:
        day = date.fromisoformat(str(value)[:10])
    except ValueError:
        return ""
    return f"{day.year}년 {day.month}월 발표"
