"""Explain bounded date-column tables through explicit row/column relationships."""
from app.services.insights.narratives.narrative_values import finite, insight, number, period, reference
from app.services.insights.narratives.table_dates import column as col
from app.services.insights.narratives.table_dates import date_axis, is_date
from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.facts.sheet_scope import narrative_sheet_groups
from app.services.insights.narratives.transposed_tables import adjacent_date_regions, transposed_region


def table_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    candidates = _table_candidates(primary) or _table_candidates(comparisons)
    if not candidates:
        return [], ""
    first_order = min(candidate[0] for candidate in candidates)
    _, items, overview, _ = max(
        (candidate for candidate in candidates if candidate[0] == first_order),
        key=lambda candidate: candidate[3],
    )
    return items[:5], overview


def _table_candidates(sheets):
    candidates = []
    for source_order, sheet in sheets:
        facts = sheet.get("business_facts", {})
        regions = list(narrative_regions(facts))
        sparse = transposed_region(regions, is_date)
        composites = adjacent_date_regions(regions, is_date)
        for region in [*regions, *composites, *([sparse] if sparse else [])]:
            result = _region_report(str(sheet["name"]), region.get("rows", []))
            if result:
                candidates.append((source_order, *result))
    return candidates

def _region_report(sheet, rows):
    header = next((axis for index, row in enumerate(rows)
                   if (axis := date_axis(rows, index, row))), None)
    if not header:
        return None
    header_index, dates = header
    menu, numeric, repeated = [], [], []
    for row in rows[header_index + 1:]:
        mapped = {col(c): c for c in row}
        values = [(date, mapped[column]) for column, date in dates.items()
                  if column in mapped]
        if len(values) < 2:
            continue
        labels = [c for c in row if col(c) < min(dates)
                  and isinstance(c.get("value"), str)]
        label = min(labels, key=col) if labels else None
        if all(finite(cell["value"]) for _, cell in values) and label:
            numeric.append(_numeric(sheet, label, values))
        elif all(isinstance(cell["value"], str) for _, cell in values):
            texts = [cell["value"] for _, cell in values]
            if (len(set(texts)) > 1 and any(
                "\n" in text or "," in text or len(text) > 25 for text in texts
            )) and not menu:
                menu.append(_text_row(sheet, label, values))
            elif label and len(set(texts)) == 1 and _not_header(row, rows):
                repeated.append((label, values))
    if not (menu or numeric):
        return None
    items = [*menu, *numeric[:3]]
    if repeated:
        items.append(_repeated(sheet, repeated[:3]))
    first, last = next(iter(dates.values())), next(reversed(dates.values()))
    overview = (f"{period(first['value'])}부터 {period(last['value'])}까지 "
                f"{len(dates)}개 날짜의 기록입니다. "
                + " ".join(item.fact for item in numeric[:2]))
    return items, overview, len(menu) * 20 + len(numeric) * 5 + len(dates)

def _evidence(sheet, label, values):
    return [reference(sheet, cell["cell"]) for cell in (
        ([label] if label else []) + [c for pair in values for c in pair]
    )]


def _text_row(sheet, label, values):
    excerpts = []
    for date, cell in values:
        text = str(cell["value"]).strip()
        parts = [part.strip("ㆍ· -") for part in text.splitlines() if part.strip()]
        sample = ", ".join(parts[:2]) if len(parts) > 2 else " ".join(parts)
        excerpts.append(f"{period(date['value'])}에는 {sample}{' 등' if len(parts) > 2 else ''}")
    name = str(label["value"]).strip() if label else "날짜별 기록"
    return insight(name, f"{' / '.join(excerpts)}이 기록되어 있습니다.",
                   _evidence(sheet, label, values))


def _numeric(sheet, label, values):
    low = min(values, key=lambda pair: pair[1]["value"])
    high = max(values, key=lambda pair: pair[1]["value"])
    name = " ".join(str(label["value"]).split())
    fact = (f"{name}의 날짜별 값은 {number(low[1]['value'])}~{number(high[1]['value'])}입니다. "
            f"가장 낮은 날은 {period(low[0]['value'])}({number(low[1]['value'])}), "
            f"가장 높은 날은 {period(high[0]['value'])}({number(high[1]['value'])})입니다.")
    if low[1]["value"] == high[1]["value"]:
        fact = f"{name}는 표시된 {len(values)}개 날짜에서 모두 {number(low[1]['value'])}입니다."
    return insight(
        f"{name}의 날짜별 차이", fact, _evidence(sheet, label, values), "trend"
    )


def _repeated(sheet, rows):
    parts, evidence = [], []
    for label, values in rows:
        parts.append(f"{str(label['value']).strip()} 항목: {len(values)}개 날짜 모두 ‘{values[0][1]['value']}’")
        evidence.extend(_evidence(sheet, label, values))
    return insight("동일하게 기록된 항목", "; ".join(parts) + "로 표기되어 있습니다.", evidence)


def _not_header(row, rows):
    """A repeated label row above varying text entries is a table subheader."""
    position = rows.index(row)
    if position + 1 < len(rows):
        following = rows[position + 1]
        data = [c["value"] for c in row if col(c) > col(min(row, key=col))]
        next_data = [c["value"] for c in following if col(c) > col(min(row, key=col))]
        if next_data and data and not set(data) & set(next_data):
            return False
    return True
