"""Question words that describe an operation, not a metric identity."""

GENERIC_METRIC_WORDS = {
    "값", "결과", "수치", "항목", "항목별", "전체", "각", "등", "현재", "최신", "최근", "최신값", "현재값",
    "최근값", "최신수치", "현재수치", "최근수치", "지금", "기준", "최대",
    "부서", "부서별", "직무", "직무별", "직원", "인원", "수", "금액", "사용량", "얼마", "어떻게", "얼마나",
    "알려줘", "보여줘", "설명해줘", "말해줘", "변화", "변동", "증감", "추이", "비교",
    "증가", "감소", "변했어", "달라졌어", "줄었어", "늘었어", "줄어", "늘어",
    "value", "values", "metric", "amount", "current", "latest", "recent", "now",
    "department", "role", "employee", "employees", "headcount", "staff",
    "change", "changed", "trend", "compare", "comparison", "increase", "decrease",
    "show", "tell", "explain", "please", "what", "which", "how", "much",
    "top", "rank", "maximum", "highest",
    "was", "were", "is", "are", "did", "has", "have", "for", "of", "in", "on",
    "at", "from", "to", "by", "and", "the", "a", "an",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "jan", "feb", "mar", "apr",
    "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}

GENERIC_METRIC_STEMS = (
    "알려", "보여", "설명", "말해", "변했", "달라졌", "줄어", "줄었", "늘어", "늘었",
    "증가", "감소", "변동", "increas", "decreas", "compar", "chang",
)

METRIC_ALIAS_COMPOUNDS = {
    "매출": ("매출액", "총매출"),
    "연구개발": ("연구개발인원",),
    "자산": ("총자산",),
    "부채": ("총부채",),
}

ALIAS_HEADER_MODIFIERS = {
    "total", "value", "amount", "usd", "krw", "eur", "jpy", "cny",
    "m", "mm", "mn", "million", "millions", "billion", "billions",
    "수", "값", "금액", "명", "천", "백만", "백만원", "억원",
}
