"""Explain comparable shares using source-backed gaps and bounded concentration."""
from decimal import Decimal

from app.services.insights.facts.fact_trends import date_value
from app.services.insights.narratives.narrative_values import finite, insight, number, reference, subject_particle
from app.services.insights.narratives.share_composition import nested, share_text, whole_of
from app.services.insights.narratives.share_narrative_basis import same_basis, share_rows
from app.services.insights.narratives.share_rank_scope import rank_scope_evidence


def share_interpretations(sheet, region, header_index, schema):
    if region.get("rows_complete") is not True:
        return []
    rows = region.get("rows", [])
    items = share_rows(rows, header_index, schema, strict=False)
    if len(items) < 2:
        return []
    headers = rows[header_index]
    title = region.get("title_cell")
    prefix = f"{title['value']}에서 " if isinstance(title, dict) else ""
    evidence = [*headers, *([title] if isinstance(title, dict) else [])]
    results = []
    ordered = sorted(items, key=lambda item: (-item["share"], item["name"]))
    high, low = ordered[:2]
    difference = high["share"] - low["share"]
    if whole_of(items) is high:
        results.append(_composition(sheet, prefix, evidence, high, low))
    elif nested(high, low):
        pass  # A group and its own member are not peers; their gap says nothing.
    elif same_basis([high, low]) and difference >= Decimal("0.005"):
        high_text, low_text = share_text(high, low)
        fact = (f"{prefix}{high['name']}의 비중은 {high_text}, "
                f"{low['name']}의 비중은 {low_text}로, "
                f"{high['name']}{subject_particle(high['name'])} {number(difference)}%p 더 높습니다.")
        results.append(_candidate(sheet, f"{high['name']}·{low['name']} 비중 차이",
                                  fact, difference, [*evidence, *high["cells"], *low["cells"]]))
    if "rank" in schema:
        concentration = _concentration(sheet, items, evidence, prefix, rows[header_index + 1:], schema)
        if concentration:
            results.insert(0, concentration)
    return results


def _concentration(sheet, items, evidence, prefix, rows, schema):
    if any(not finite(item["rank"])
           or int(item["rank"]) != item["rank"] for item in items):
        return None
    ordered = sorted(items, key=lambda item: item["rank"])
    if len({item["rank"] for item in ordered}) != len(ordered):
        return None
    selected = ordered[:5]
    if ([item["rank"] for item in selected] != list(range(1, len(selected) + 1))
            or not same_basis(selected)
            or any(a["share"] < b["share"] for a, b in zip(selected, selected[1:]))):
        return None
    identities = rank_scope_evidence(rows, schema, selected)
    if identities is None:
        return None
    total = sum((item["share"] for item in selected), Decimal(0))
    if not 0 < total <= 100:
        return None
    details = ", ".join(f"{item['name']} {text}" for item, text in zip(selected, share_text(*selected)))
    fact = (f"{prefix}{_as_of(selected)}상위 {len(selected)}개 항목의 비중 합계는 "
            f"{number(total)}%입니다. 구성은 {details}입니다.")
    return _candidate(sheet, f"상위 {len(selected)}개 항목의 비중 합계", fact, total,
                      [*evidence, *identities, *(cell for item in selected for cell in item["cells"])],
                      kind="concentration")


def _composition(sheet, prefix, evidence, whole, part):
    """The largest part as a slice of its whole, not as a rival of the whole."""
    whole_text, part_text = share_text(whole, part)
    within = number(round(part["quantity"] / whole["quantity"] * 100, 1))
    fact = (f"{prefix}{whole['name']}의 비중은 {whole_text}이고, 이 가운데 가장 큰 항목은 "
            f"{part['name']}({part_text})로 {whole['name']}의 {within}%를 차지합니다.")
    return _candidate(sheet, f"{whole['name']} 중 {part['name']} 비중", fact, part["share"],
                      [*evidence, *whole["cells"], *part["cells"]])


def _as_of(selected):
    """One shared record date for every listed holder, said once."""
    days = {found.date() for item in selected for _, value in item["scope"]
            if (found := date_value(value)) is not None}
    return f"{next(iter(days)):%Y년 %-m월 %-d일} 기준 " if len(days) == 1 else ""


def _candidate(sheet, title, fact, weight, cells, kind="interpretation"):
    return kind, float(weight), insight(
        title, fact, [reference(sheet, cell["cell"]) for cell in cells], "metric", topic=title,
    )
