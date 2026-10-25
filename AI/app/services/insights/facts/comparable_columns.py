"""Classify comparable-transaction headers by financial role, never by file.

A multiple is "price per unit of earnings" and is the only price-level measure.
Amounts (transaction, equity or enterprise value) measure deal size. Earnings
columns can become a multiple's denominator. Roles come from header wording
that data providers and analysts share, so another workbook with the same
kinds of fields is read the same way.
"""
import re

TARGET_NAME = re.compile(r"target.*(?:issuer.*)?name|피인수.*(?:기업|대상).*(?:이름|명)", re.I)
_MULTIPLE = re.compile(r"\(\s*x\s*\)|\bmultiples?\b|배수|\(\s*배\s*\)", re.I)
_PER_UNIT = re.compile(r"\(\s*%\s*\)|per\s+share|주당|percent|비율|%", re.I)
EARNINGS = {
    "net_income": re.compile(r"net\s+(?:income|earnings)|순이익", re.I),
    "ebitda": re.compile(r"\bebitda\b", re.I),
    "ebit": re.compile(r"\bebit\b", re.I),
    "revenue": re.compile(r"\brevenues?\b|\bsales\b|매출", re.I),
    "book": re.compile(r"book\s+value|장부\s*가|순자산", re.I),
}
_EQUITY = re.compile(r"equity\s+value|market\s+cap|지분\s*가치|시가\s*총액", re.I)
_ENTERPRISE = re.compile(r"enterprise\s+value|기업\s*가치", re.I)
_INDUSTRY = re.compile(r"industry|sector|업종|산업", re.I)
_BUYER = re.compile(r"buyer|acquirer|investor|인수자|매수자", re.I)
_ADVISER = re.compile(r"advis|자문", re.I)
_ANNOUNCED = re.compile(r"announc|발표", re.I)
TARGET_SIDE = re.compile(r"target|issuer|피인수|대상", re.I)
BUYER_SIDE = re.compile(r"acquirer|buyer|인수자|매수자", re.I)


def column_role(label):
    """Return (role, detail, priority) for one header label, or None."""
    text = " ".join(str(label).split())
    lowered = text.casefold()
    denominator = text.rsplit("/", 1)[1] if "/" in text else ""
    basis = earnings_kind(denominator) if denominator else None
    if (_MULTIPLE.search(text) or basis) and not _PER_UNIT.search(text) and (basis or denominator):
        return "multiple", basis or _clean(denominator), 2 if "transaction" in lowered else 1
    if "/" not in text and not _PER_UNIT.search(text):
        if "total transaction value" in lowered or "총 거래가치" in text:
            return "size", None, 2
        if re.search(r"transaction value|거래\s*(?:가치|금액)", text, re.I):
            return "size", None, 1
        if _EQUITY.search(text):
            return "equity", None, 1
        if _ENTERPRISE.search(text):
            return "enterprise", None, 1
        if kind := earnings_kind(text):
            return "earnings", kind, 1
    if _INDUSTRY.search(text):
        return "industry", None, 1
    if _BUYER.search(text) and not _ADVISER.search(text) and not TARGET_SIDE.search(text):
        return "buyer", None, 1
    if _ANNOUNCED.search(text):
        return "announced", None, 1
    return None


_ABBREVIATED = {"e": "net_income", "b": "book", "bv": "book", "s": "revenue"}  # P/E, P/B, P/S


def earnings_kind(text):
    short = re.sub(r"\(\s*(?:x|배)\s*\)", " ", str(text), flags=re.I).strip().casefold()
    return _ABBREVIATED.get(short) or next(
        (key for key, pattern in EARNINGS.items() if pattern.search(str(text))), None)


def _clean(text):
    return " ".join(re.sub(r"\(\s*x\s*\)|\(\s*배\s*\)", " ", str(text), flags=re.I).split())
