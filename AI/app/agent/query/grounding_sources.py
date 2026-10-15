"""Small helpers for building the lexical grounding source set."""

from app.agent.query.references import normalize_reference


REPORTING_LANGUAGE = (
    "단 다만 자료 해석 신중해야 합니다 신뢰도 주의 필요합니다 대표성 한계 확인되는 "
    "확인된 것 건뿐이어서 건뿐이므로 불과 감소했고 증가했고 감소하며 증가하며"
)


def cited_references(evidence: list[object]) -> set[str]:
    references = set()
    for item in evidence:
        reference = getattr(item, "reference", None)
        sheet = getattr(item, "sheet_name", None)
        if reference and sheet:
            normalized = normalize_reference(f"{sheet}!{reference}")
            if normalized:
                references.add(normalized)
    return references


def evidence_sources(evidence: list[object]) -> list[str]:
    return [
        str(value)
        for item in evidence
        for value in (
            getattr(item, "description", None),
            getattr(item, "value", None),
            getattr(item, "formula", None),
        )
        if value is not None
    ]


def semantic_units(sources: list[str]) -> list[str]:
    text = " ".join(sources).casefold()
    aliases = (
        (("employee", "headcount", "직원", "인원"), "직원 인원 명"),
        (("transaction", "거래"), "거래"),
        (("multiple", "(x)", "배수"), "배 배수"),
        (("$m", "million", "백만 달러"), "백만 달러"),
        (("event", "development", "announcement", "이벤트"),
         "이벤트 발표 공시 소식"),
    )
    return [words for markers, words in aliases if any(item in text for item in markers)]
