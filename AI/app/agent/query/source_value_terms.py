"""Split a value question into source terms; anything left unexplained blocks.

The glossary maps common Korean business wording to label fragments used by
English or Korean workbooks. It is used only by the consensus lookup, so the
routing of every other answer path is unchanged.
"""
import re

FIELD_TERMS = {
    "직원 수": ("employees", "headcount", "직원"), "직원수": ("employees", "headcount", "직원"),
    "직원": ("employees", "headcount", "직원"), "인원": ("employees", "headcount", "인원"),
    "근속 기간": ("tenure", "근속"), "평균": ("average", "avg", "mean", "평균"),
    "지분율": ("percent held", "percent owned", "ownership (%)", "지분율"),
    "보유 주식 수": ("shares held", "shares owned", "보유 주식"),
    "기관 투자자": ("institution", "기관"), "내부자": ("insider", "내부자"),
    "인수자": ("buyer", "acquirer", "인수자"), "매수자": ("buyer", "acquirer", "매수자"),
    "거래 금액": ("transaction value", "deal value", "거래 금액", "거래금액"),
    "시가총액": ("market cap", "market capitalization", "시가총액"), "주당순이익": ("eps", "주당순이익"),
    "eps": ("eps",), "per": ("p/ e", "p / e", "p/e", "price/ eps", "price/eps", "per"),
    "roe": ("return on equity", "roe"), "배수": ("(x)", "multiple", "배수"),
    "비중": ("percent", "%", "비중"), "마진": ("margin", "마진"), "이익률": ("margin", "이익률"),
}
MEASURES = frozenset({"직원 수", "직원수", "직원", "인원"})
RATIO_TERMS = frozenset({"배수", "per", "비중", "마진", "이익률", "지분율"})
# "평균" names a field ("Average Tenure"), never a row: "S&P Average ETF" is a holder.
FIELD_ONLY = frozenset({"평균"})
# Request wording and particles: how to answer, not which source value.
GENERIC = frozenset({
    "알려줘", "보여줘", "말해줘", "뭐야", "누구야", "얼마야", "얼마", "몇", "명", "개", "있어", "있니", "현재", "지금",
    "값", "수", "수치", "이야", "야", "좀", "줘", "누구", "무엇", "뭐", "상태", "기준", "어때", "어떻게", "돼", "되나",
    "인가", "인지", "확인해줘", "궁금해", "알고", "싶어", "최근", "최신", "가장최근", "latest", "current", "what", "is",
})
# Superlatives, totals, lists, trends and comparisons are not one source value.
NOT_A_LOOKUP = re.compile(
    r"합계|총합|중앙값|최대|최소|최고|최저|가장|제일|상위|하위|순위|추이|변화|변동|증감|늘었|줄었|목록|리스트|비교|대비|평균값|"
    r"몇\s*(?:건|개|대|곳|가지|번)|건수|개수|분포|전체|모든|각각|별로|이상|이하|초과|미만|제외|포함|"
    r"\b(?:top|list|trend|compare|sum|total of|how many|average of|median|max|min)\b", re.I)
_PERIOD = re.compile(r"(?<!\d)((?:19|20)\d{2})\s*년(?:\s*(\d{1,2})\s*월)?")
_PARTICLE = re.compile(r"(?:이야|이에요|예요|으로|에서|은|는|이|가|을|를|의|에|도|만|야|로)$")


def tokens(text):
    return re.findall(r"#\d+|\d+(?:\.\d+)+|[a-z][a-z0-9]*|[가-힣]+|\d+", str(text).casefold())


def question_terms(question):
    """(period, fields, words) or None when the question is not a lookup."""
    if NOT_A_LOOKUP.search(question):
        return None
    text = " ".join(question.casefold().split())
    found = _PERIOD.search(text)
    period = (int(found.group(1)), int(found.group(2)) if found.group(2) else None) if found else None
    rest = _PERIOD.sub(" ", text)
    if re.search(r"(?<!\d)\d{1,2}\s*월|(?<!\d)\d{1,2}\s*일", rest):
        return None  # a month or day without its year is not a bounded period
    fields = []
    for phrase in sorted(FIELD_TERMS, key=len, reverse=True):
        pattern = (rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])" if phrase.isascii()
                   else re.escape(phrase))
        if re.search(pattern, rest):
            fields.append(phrase)
            rest = re.sub(pattern, " ", rest)
    words = []
    for token in tokens(rest):
        base = _PARTICLE.sub("", token) if re.fullmatch(r"[가-힣]+", token) else token
        if token not in GENERIC and base not in GENERIC and base:
            words.append(base)
    return (period, tuple(fields), tuple(dict.fromkeys(words))) if fields or words else None


def covers(term, text):
    """A glossary term or literal word appears in a source label."""
    low = " ".join(str(text).casefold().split())
    if term in FIELD_TERMS:
        return any(alias in low for alias in FIELD_TERMS[term])
    if re.fullmatch(r"[가-힣]+", term):
        return term in low
    return term in tokens(low)
