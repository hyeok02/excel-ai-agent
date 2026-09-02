import re

from app.agent.query.index import IndexedRow

STOP_WORDS = {
    "알려줘", "보여줘", "무엇", "어떤", "엑셀", "파일", "가장", "높은", "낮은",
    "얼마", "어디", "대한", "있는", "해줘", "the", "what", "which", "show",
}
SEMANTIC_ALIASES = {
    "직원": ("headcount", "employee", "employees", "workforce"),
    "인원": ("headcount", "employee", "employees", "workforce"),
    "부문": ("department", "function", "division", "segment"),
    "부서": ("department", "function", "division"),
    "매출": ("revenue", "sales"),
    "영업이익": ("operating income", "operating profit"),
    "순이익": ("net income", "net profit"),
    "자산": ("asset", "assets"),
    "부채": ("debt", "liability", "liabilities"),
    "현금": ("cash",),
    "날짜": ("date", "dates"),
    "비율": ("rate", "ratio", "%"),
}
KOREAN_SUFFIXES = (
    "으로부터", "에서부터", "에게서", "으로", "까지", "부터", "처럼", "보다",
    "에서", "에게", "께서", "와", "과", "을", "를", "은", "는", "이", "가",
    "의", "에", "도", "만",
)


def search_terms(query: str) -> list[str]:
    tokens = re.findall(r"[0-9a-zA-Z_]+|[가-힣]+", query.casefold())
    normalized = [_strip_korean_suffix(token) for token in tokens]
    terms = [token for token in normalized if len(token) >= 2 and token not in STOP_WORDS]
    aliases = [
        alias
        for term in terms
        for concept, values in SEMANTIC_ALIASES.items()
        if concept in term
        for alias in values
    ]
    return list(dict.fromkeys([*terms, *aliases]))


def relevance(row: IndexedRow, terms: list[str]) -> int:
    sheet_text = row.sheet_name.replace("_", " ").casefold()
    return sum(4 if term in row.search_text else 8 if term in sheet_text else 0 for term in terms)


def _strip_korean_suffix(token: str) -> str:
    for suffix in KOREAN_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix):
            return token[: -len(suffix)]
    return token
