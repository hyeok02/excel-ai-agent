"""Conservative display labels for record headers, never for source values.

These names only change the prose after the source columns have been selected.
Unknown labels and business qualifiers stay intact; no currency is inferred.
"""
import re


_HEADERS = {
    "total price": "금액", "total amount": "금액", "amount": "금액",
    "quantity": "수량", "qty": "수량", "units": "수량",
    "unit price": "단가", "unit cost": "단위 비용",
    "category": "분류", "group": "그룹", "type": "유형",
    "region": "지역", "city": "도시", "status": "상태",
    "product": "제품", "department": "부서", "role": "직무",
    "revenue": "매출", "total revenue": "총매출",
    "insured value": "보험가액", "premium": "보험료",
    "count": "건수", "total count": "전체 건수",
}

# Display translations of explicit source nouns, never a classifier for values
# or filenames. Unknown subjects retain their source spelling.
_SUBJECTS = {
    "food": "식품", "beverage": "음료", "beverages": "음료",
    "electronics": "전자제품", "clothing": "의류", "apparel": "의류",
    "book": "도서", "books": "도서", "furniture": "가구",
    "office supplies": "사무용품", "office supply": "사무용품",
    "product": "제품", "products": "제품",
}

# Independent noun translations for declared table subjects.  These are display
# vocabulary, not file detectors: the table definition and column schema must
# establish the subject before this helper is used.
_RECORD_MODIFIERS = {
    "commercial": "상업용", "residential": "주거용", "property": "부동산",
    "vehicle": "차량", "motor": "자동차", "health": "건강", "life": "생명",
    "employee": "직원", "employees": "직원", "customer": "고객", "customers": "고객",
    "inventory": "재고", "stock": "재고", "equipment": "장비",
    "maintenance": "유지보수", "purchase": "구매", "sales": "판매",
    "attendance": "근태", "absence": "결근", "expense": "비용", "expenses": "비용",
    "invoice": "청구서", "invoices": "청구서", "order": "주문", "orders": "주문",
    "contract": "계약", "contracts": "계약", "payment": "결제", "payments": "결제",
}


def declared_record_label(value, *, insurance=False):
    """Translate a complete explicit subject, retaining unknown qualifiers.

    ``policy`` alone is ambiguous (a company rule or an insurance contract).
    Calling code must establish the insurance meaning from the source schema.
    A partial translation must never erase an unknown qualifier like forecast.
    """
    words = header_words(value)
    if insurance:
        match = re.fullmatch(r"(?:(.*?)\s+)?(?:insurance\s+)?polic(?:y|ies)", words)
        if match:
            modifier = re.sub(r"(?:^|\s)insurance$", "", match[1] or "").strip()
            translated = [_RECORD_MODIFIERS.get(word) for word in modifier.split()]
            if all(translated):
                return " ".join(translated), "보험 계약"
    if re.search(r"[가-힣]", value):
        return value.strip(), "기록"
    translated = [_RECORD_MODIFIERS.get(word) for word in words.split()]
    if translated and all(translated):
        return " ".join(translated), "기록"
    return f"‘{value.strip()}’", "기록"


def record_group_label(value, headers):
    """Disambiguate a generic State header only with geographic schema context."""
    names = {header_words(cell["value"]) for cell in headers.values()}
    if header_words(value) == "state" and names & {"city", "region", "country", "location"}:
        return "지역(State)"
    return record_header(value)


def header_words(value, *, keep_case=False):
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", str(value))
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = " ".join(re.sub(r"[_\-]+", " ", text).split())
    return words if keep_case else words.casefold()


def record_header(value, kind="기록"):
    words = header_words(value)
    activity = {"판매 내역": "판매", "구매 내역": "구매"}.get(kind)
    if activity and words in {"total price", "total amount", "amount", "금액"}:
        return f"{activity}금액"
    if activity and words in {"quantity", "qty", "units", "수량"}:
        return f"{activity}수량"
    return _HEADERS.get(words, str(value).strip())


def record_subject(value):
    if re.search(r"[가-힣]", str(value)):
        return str(value).strip()
    return _SUBJECTS.get(header_words(value), f"‘{str(value).strip()}’")


def record_kind(sheet, headers):
    """Call records sales only with explicit source context and transaction columns.

    Quantity and price also occur in purchases. A Sales department alone is not
    evidence of sales transactions, nor is the workbook filename.
    """
    words = header_words(sheet)
    names = {header_words(c["value"]) for c in headers.values()}
    transactions = (names & {"quantity", "qty", "units", "수량"}
                    and names & {"unit price", "단가"}
                    and names & {"total price", "total amount", "금액"})
    sales = re.search(r"\bsales\b|판매", words)
    purchases = re.search(r"\bpurchases?\b|구매", words)
    if transactions and not restricted_activity(words) and bool(sales) != bool(purchases):
        return "판매 내역" if sales else "구매 내역"
    return "기록"


def restricted_activity(text):
    """An explicit qualifier vetoes a transaction interpretation from a title."""
    return bool(re.search(
        r"\b(?:returns?|forecast|budget|planned|department|roles?|not|non)\b"
        r"|반품|예측|예산|계획|부서|직무|아닌|아님", header_words(text),
    ))
