"""Source-word translations for prose, independent of workbook names and values.

This layer never selects a measure or invents a domain from numeric data. It
translates explicit terms, keeping unrecognised qualifiers and original labels
in the evidence. A role named Sales is deliberately not translated as revenue.
"""
import calendar
import re

from app.services.insights.display.glossary import translate

# A reusable vocabulary, not full table captions: modifiers are composed below.
_TERMS = {
    "population estimates": "인구 추정치", "population estimate": "인구 추정치",
    "population": "인구", "asthma attack prevalence": "천식 발작 경험 비율",
    "current asthma prevalence": "현재 천식 유병률", "asthma prevalence": "천식 유병률",
    "air quality": "대기질", "greenhouse gas emissions": "온실가스 배출량",
    "carbon dioxide emissions": "이산화탄소 배출량", "emissions": "배출량",
    "average price of electricity": "평균 전기요금", "electricity prices": "전기요금",
    "electricity price": "전기요금", "electricity generation": "발전량",
    "net generation": "순발전량", "generation": "발전량",
    "occupancy rate": "점유율", "beds occupied": "사용 병상 수",
    "occupied beds": "사용 병상 수", "beds available": "가용 병상 수",
    "available beds": "가용 병상 수", "beds": "병상",
    "electricity supply": "전력 공급", "fuel supply": "연료 공급",
    "domestic transport": "국내 운송", "buildings and product uses": "건물·제품 사용",
    "residential": "가정용", "commercial": "상업용", "industrial": "산업용",
    "transportation": "수송용", "all sectors": "전체 부문",
    "united kingdom": "영국", "uk": "영국", "u.k.": "영국",
    "u.s.": "미국", "united states": "미국",
    "great britain": "그레이트브리튼", "england": "잉글랜드", "wales": "웨일스",
    "scotland": "스코틀랜드", "northern ireland": "북아일랜드",
    "north east": "북동부", "north west": "북서부", "south east": "남동부",
    "south west": "남서부", "grand total": "총합계", "total": "전체", "annual totals": "연간 합계",
    "year to date": "연초 이후 누적", "ytd": "연초 이후 누적",
    "acute trusts": "급성기 의료기관", "all": "모든",
    "estimated": "추정", "estimate": "추정", "provisional": "잠정",
    "forecast": "전망", "budget": "예산", "actual": "실적",
}
_UNITS = {
    "cents per kilowatthour": "센트/kWh", "cents per kilowatt hour": "센트/kWh",
    "dollars per megawatthour": "달러/MWh", "dollars per megawatt hour": "달러/MWh",
    "thousand megawatthours": "천 MWh", "thousand megawatt hours": "천 MWh",
    "megawatthours": "MWh", "megawatt hours": "MWh",
    "kilowatthours": "kWh", "kilowatt hours": "kWh",
    "million tonnes carbon dioxide equivalent": "백만 톤 CO₂환산량",
    "million tonnes of carbon dioxide equivalent": "백만 톤 CO₂환산량",
    "tonnes carbon dioxide equivalent": "톤 CO₂환산량",
    "thousand persons": "천 명", "thousands of persons": "천 명",
    "persons": "명", "people": "명", "percent": "%", "percentage": "%",
}
_AIR = {"good": "좋음", "moderate": "보통", "unhealthy": "건강에 해로움",
        "unhealthy for sensitive groups": "민감군에 해로움", "very unhealthy": "매우 해로움",
        "hazardous": "위험", "no monitoring data": "측정자료 없음"}


def source_label(value, context=""):
    """Translate known source words while retaining unknown qualifiers verbatim."""
    text = " ".join(str(value or "").split())
    if not text or re.search(r"[가-힣]", text):
        return text
    # Hierarchical headings can repeat the exact same total marker. Keep the
    # parent's scope and every other qualifier; remove only that duplicate.
    text = re.sub(r"(\btotal)\s*·\s*total$", r"\1", text, flags=re.I)
    caption = re.fullmatch(
        r"percentage of days with .+? air quality for (.+?)(?:,\s*((?:19|20|21)\d{2})[-–]((?:19|20|21)\d{2}))?",
        text, re.I,
    )
    if caption:
        subject = source_label(caption[1])
        years = f" ({caption[2]}~{caption[3]}년)" if caption[2] else ""
        return f"{subject}의 대기질별 일수 비율{years}"
    scope = f"{context} {text}"
    if re.search(r"\bair\s+quality\b|대기질", scope, re.I) and text.casefold() in _AIR:
        return _AIR[text.casefold()]
    # G&A is ambiguous outside a bed/acute-care context; never guess from the
    # abbreviation alone (it can also mean general & administrative).
    if re.search(r"\bbeds?\b|acute|hospital|병상", scope, re.I):
        text = re.sub(r"\bG\s*&\s*A\s+occupancy rate\b", "일반·급성기 병상 점유율", text, flags=re.I)
        text = re.sub(r"\bG\s*&\s*A\b", "일반·급성기", text, flags=re.I)
        text = re.sub(r"\badult\b", "성인", text, flags=re.I)
        # Standalone nested column qualifiers need the parent bed context.
        text = re.sub(r"(?<!beds )\bavailable\b(?!\s+beds)", "가용", text, flags=re.I)
        text = re.sub(r"(?<!beds )\boccupied\b(?!\s+beds)", "사용", text, flags=re.I)
    match = re.fullmatch(r"(total\s+)?generation\s+at\s+(.+)", text, re.I)
    if match:
        facilities = re.sub(r"\butility[ -]scale\s+facilities\b", "대규모 발전시설", match[2], flags=re.I)
        return f"{facilities}의 {'총' if match[1] else ''}발전량"
    # Exact financial terms retain the existing glossary, except 'Sales': a
    # category/role label cannot acquire the meaning of a revenue measure.
    direct = translate(text) if text.casefold() != "sales" else ""
    if direct:
        return direct
    pattern = r"(?<![A-Za-z])(?:" + "|".join(re.escape(t) for t in sorted(_TERMS, key=len, reverse=True)) + r")(?![A-Za-z])"
    text = re.sub(pattern, lambda m: _TERMS[m[0].casefold()], text, flags=re.I)
    text = re.sub(r"\bmid[ -]?year\b", "연중", text, flags=re.I)
    text = re.sub(r"\bchildren\s+(?:ages?|aged)\s+(\d+)\s+(?:to|[–-])\s+(\d+)\s*(?:years)?\b", r"\1~\2세 아동", text, flags=re.I)
    text = re.sub(r"\bchildren\b", "아동", text, flags=re.I)
    text = re.sub(r"(?<=[가-힣])\s+and\s+(?=[가-힣])", "·", text, flags=re.I)
    text = re.sub(r"^전체\s+([가-힣].+)$", r"총 \1", text)
    return text


def source_unit(value):
    text = " ".join(str(value or "").split())
    return _UNITS.get(text.casefold(), text)


def source_caption(value):
    """Read explicit table captions without replacing an unknown source topic.

    These are reusable noun/modifier constructions, rather than workbook/title
    lookups. Numeric dates, provisional/forecast flags and unfamiliar names
    survive so a concise description cannot silently broaden the source scope.
    """
    text = " ".join(str(value or "").split())
    text = re.sub(r"^(?:table|indicator)\s+[A-Za-z]*\d+(?:\.\d+)*(?:\.?[A-Za-z])?\s*[.:–-]?\s*", "", text, flags=re.I)
    text = re.sub(r"^[A-Z]{2,}\d+\s*:\s*", "", text)
    if not text:
        return ""
    beds = re.fullmatch(r"number of (.+? beds) by (.+?) averaged over (?:a )?complete month\.?\s*(?:data for (.+?)\.?)?", text, re.I)
    if beds:
        measure = source_label(re.sub(r"available and occupied beds", "beds available · beds occupied", beds[1], flags=re.I))
        dimension = "병상 유형" if beds[2].casefold() == "bed type" else source_label(beds[2])
        scope = source_label(beds[3].rstrip(".")) if beds[3] else ""
        return f"{scope + '의 ' if scope else ''}{dimension}별 월평균 {measure}"
    # A population summary's geographic qualifier belongs with its measure.
    text = re.sub(r"\b(population estimates?)\s*:\s*summary for\s+(?:the\s+)?([^,]+)",
                  lambda m: f"{source_label(m[2])} {source_label(m[1])} 요약", text, flags=re.I)
    age = re.fullmatch(r"percentage of (.+?) with asthma(?:,\s*(.*))?", text, re.I)
    if age:
        text = f"{source_label(age[1])}의 천식 유병률" + (f", {age[2]}" if age[2] else "")
    # Keep every unmatched remainder, including source-specific qualifiers.
    caption_terms = {
        "territorial": "국내 발생", "by gas": "가스별",
        "by end-use sector": "용도별", "by energy source": "에너지원별",
        "to ultimate customers": "최종 소비자 대상", "by state": "주별",
        "available and occupied beds": "가용·사용 병상 수",
        "by bed type": "병상 유형별", "averaged over a complete month": "월평균",
        "number of": "수량:", "data for": "대상:", "summary": "요약",
    }
    pattern = r"(?<![A-Za-z])(?:" + "|".join(re.escape(t) for t in sorted(caption_terms, key=len, reverse=True)) + r")(?![A-Za-z])"
    text = re.sub(pattern, lambda m: caption_terms[m[0].casefold()], text, flags=re.I)
    # source_label intentionally leaves pre-existing Korean alone; translate
    # each remaining English run after the caption grammar added Korean words.
    text = re.sub(r"[A-Za-z][A-Za-z0-9 &().,'/\-]*[A-Za-z.)]|[A-Za-z]+",
                  lambda m: source_label(m[0]), text)
    for original in sorted(_UNITS, key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z])(?:in\s+)?" + re.escape(original) + r"(?![A-Za-z])",
                      f"단위: {_UNITS[original]}", text, flags=re.I)
    text = re.sub(r"\bmid[- ]((?:19|20|21)\d{2})\s+(?:to|[-–])\s+mid[- ]((?:19|20|21)\d{2})\b",
                  r"\1년 중반~\2년 중반", text, flags=re.I)
    text = re.sub(r"\b((?:19|20|21)\d{2})\s*(?:to|[-–])\s*((?:19|20|21)\d{2})\b",
                  r"\1~\2년", text, flags=re.I)
    for month in range(1, 13):
        text = re.sub(r"\b" + calendar.month_name[month] + r"\s+((?:19|20|21)\d{2})\b",
                      lambda m: f"{m[1]}년 {month}월", text, flags=re.I)
    text = re.sub(r"((?:19|20|21)\d{2}년(?: \d{1,2}월)?)\s+and\s+((?:19|20|21)\d{2})(?!\d)",
                  r"\1 및 \2년", text, flags=re.I)
    return " ".join(text.split()).strip(" .")


def caption_measure(value):
    """A measure named by a bound caption; values never supply its meaning."""
    text = " ".join(str(value or "").split())
    if re.search(r"\bpopulation estimates?\b", text, re.I):
        if re.search(r"growth|change|percent|rate|ratio|density|index|per\s+|thousand|million|천|백만|비율|밀도|지수|증감", text, re.I):
            return "", ""
        return "인구 추정치", "명"
    if re.search(r"\baverage price of electricity\b", text, re.I):
        return "평균 전기요금", ""
    if re.search(r"\belectricity prices?\b", text, re.I):
        return "전기요금", ""
    if re.search(r"\bgreenhouse gas emissions\b", text, re.I):
        return "온실가스 배출량", ""
    return "", ""


def section_label(value):
    text = " ".join(str(value or "").split())
    match = re.fullmatch(r"year\s+((?:19|20|21)\d{2})", text, re.I)
    return f"{match[1]}년" if match else source_label(text)


def narrative_scope(sheet, section=""):
    """Skip opaque technical names, not human geographic/entity qualifiers."""
    name = " ".join(str(sheet or "").split())
    if re.fullmatch(r"(?:sheet|table|시트)[ _\d.\-]*", name, re.I):
        name = ""
    name = re.sub(r"^time\s*series\s+", "", name, flags=re.I)
    parts = [source_label(name), section_label(section)]
    return " · ".join(dict.fromkeys(p for p in parts if p))
