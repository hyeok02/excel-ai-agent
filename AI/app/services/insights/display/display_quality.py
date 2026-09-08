"""Rules for keeping internal identifiers out of user-facing insights."""
import re


PROVIDER_CODE = re.compile(
    r"^(?:IQ|SP|MI)_[A-Z0-9_]+$|^SPTR(?:D|O)\d+$|^'[\d,]+'[,]?$",
    re.I,
)
DATA_LIKE_LABEL = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:T.*)?$|\$|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ,]",
    re.I,
)
IDENTIFIER_LABEL = re.compile(
    r"(?:^|[\s_>/(-])(?:id|oid|identifier|code)(?:$|[\s_>)/-])|식별자|코드",
    re.I,
)
GENERIC_LABELS = {"na", "n/a", "none", "null", "value", "값", "percentage"}
BUSINESS_TERMS = (
    "total revenue",
    "revenue",
    "net income",
    "ebitda",
    "ebit",
    "gross profit",
    "operating income",
    "cash",
    "total assets",
    "total debt",
    "headcount",
    "employee",
    "매출",
    "순이익",
    "영업이익",
    "자산",
    "부채",
    "현금",
    "직원",
    "인원",
)


def is_machine_value(value: object) -> bool:
    text = " ".join(str(value).split())
    return bool(PROVIDER_CODE.fullmatch(text))


def is_identifier_label(value: object) -> bool:
    text = " ".join(str(value).split())
    return bool(not text or text.isdigit() or PROVIDER_CODE.fullmatch(text)
                or IDENTIFIER_LABEL.search(text))


def is_presentable_label(value: object) -> bool:
    text = " ".join(str(value).split())
    return bool(text and len(text) <= 80 and text.casefold() not in GENERIC_LABELS
                and not is_identifier_label(text))


def is_field_label(label: object, raw: object) -> bool:
    text = " ".join(str(label).split())
    value = " ".join(str(raw).split())
    return bool(is_presentable_label(text) and text.casefold() != value.casefold()
                and text.count(",") < 2 and not DATA_LIKE_LABEL.search(text))


def business_priority(value: object) -> int:
    text = " ".join(str(value).split()).casefold()
    for index, term in enumerate(BUSINESS_TERMS):
        if term in text:
            return len(BUSINESS_TERMS) - index
    return 0


def metric_family(value: object) -> str:
    text = " ".join(str(value).split()).casefold()
    families = (
        ("revenue", ("revenue", "매출")),
        ("net_income", ("net income", "순이익")),
        ("ebitda", ("ebitda",)),
        ("ebit", ("ebit", "영업이익")),
        ("profit", ("profit", "이익")),
        ("headcount", ("headcount", "employee", "직원", "인원")),
        ("assets", ("assets", "자산")),
        ("debt", ("debt", "부채")),
        ("cash", ("cash", "현금")),
    )
    return next((name for name, terms in families if any(term in text for term in terms)), "")
