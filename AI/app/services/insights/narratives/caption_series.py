"""Attach a table's measure only to a positively identified measure/category.

A population table can also contain births, areas or rates. Its caption alone
does not turn every numeric row into a population count.
"""
import re

from openpyxl.utils.cell import coordinate_to_tuple

from app.services.insights.display.derived_metrics import derived_metric
from app.services.insights.display.source_labels import caption_measure
from app.services.insights.facts.series_scalars import scalar, unit
from app.services.insights.narratives.narrative_values import reference

_GEOGRAPHY = re.compile(r"^(?:geography|country|state|region|district|location|국가|지역|시도|지리 구분)$", re.I)
_GEOGRAPHIC_KIND = re.compile(r"^(?:country|state|region|district|county|city|unitary authority|local authority|국가|지역|도시)$", re.I)
_NAMED_GEOGRAPHY = re.compile(
    r"^(?:United Kingdom|UK|U\.K\.|U\.S\.|United States|Great Britain|England|Wales|"
    r"Scotland|Northern Ireland|North East|North West|South East|South West)"
    r"(?:\s+(?:and\s+(?:England|Wales)|Total))?$", re.I)
_MEASURE_ROW = re.compile(
    r"\b(?:births?|deaths?|age|area|density|index|revenue|sales|income|profit|"
    r"customers?|employees?|accounts?|households?|consumption|demand|capacity)\b|"
    r"출생|사망|연령|면적|밀도|지수|매출|고객|직원|가구|소비량|수요|용량", re.I)
_ENERGY_PRICE_UNIT = re.compile(r"^(?:cents|dollars) per (?:kilo|mega)watt\s?hour$", re.I)
_SECTOR = re.compile(r"^(?:residential|commercial|industrial|transportation|all sectors)$", re.I)


def qualified_series_caption(sheet, series, caption, refs):
    measure, count_unit = caption_measure(caption)
    if not measure:
        return "", "", ()
    # A caption naming several measures does not tell us which one a numeric
    # category row uses. Conjunctions inside later by/for qualifiers (e.g.
    # 'for England and Wales') do not make a single measure ambiguous.
    heading = re.split(r"\b(?:by|for)\b", str(caption), maxsplit=1, flags=re.I)[0]
    if re.search(r"\b(?:and|versus|vs)\b|[&/]", heading, re.I):
        return "", "", ()
    metric = str(series.get("metric", "")).strip()
    qualifiers = f"{series.get('scope') or ''} {series.get('basis') or ''} {metric}"
    points = series.get("observations") or series.get("points", [])
    if derived_metric(qualifiers, points) or _MEASURE_ROW.search(qualifiers):
        return "", "", ()
    geographic, geographic_refs = _geographic_dimension(sheet, series)
    explicit_population = bool(re.fullmatch(r"(?:total |estimated )?population(?: estimates?)?", metric, re.I))
    explicit_price = bool(re.search(r"\belectricity prices?\b|\bprice of electricity\b", metric, re.I))
    explicit_emissions = bool(re.search(r"\b(?:greenhouse gas |carbon dioxide )?emissions\b", metric, re.I))
    if measure == "인구 추정치":
        if not (geographic or explicit_population):
            return "", "", ()
        # A contradictory cell/declared unit must never be hidden by the noun.
        units = {unit(point) for point in points} - {""}
        declared = str((series.get("declared_unit") or {}).get("value", "")).strip()
        if units - {"명", "천 명", "백만 명", "천", "백만"} or declared and not re.fullmatch(
                r"(?:thousands? of |thousand |millions? of |million )?(?:persons|people)|명|천 명|백만 명", declared, re.I):
            return "", "", ()
        if any(not scalar(p.get("value")) or not float(p["value"]).is_integer() for p in points):
            count_unit = ""
    elif "전기요금" in measure:
        declared = str((series.get("declared_unit") or {}).get("value", "")).strip()
        if not (explicit_price or (geographic or _SECTOR.fullmatch(metric)) and _ENERGY_PRICE_UNIT.fullmatch(declared)):
            return "", "", ()
    elif measure == "온실가스 배출량" and not explicit_emissions:
        return "", "", ()
    return measure, count_unit, [*refs, *geographic_refs]


def _geographic_dimension(sheet, series):
    metric = str(series.get("metric", "")).strip()
    if _NAMED_GEOGRAPHY.fullmatch(metric):
        return True, []  # The metric's original cell is already evidence.
    try:
        label_row, label_col = coordinate_to_tuple(series["label_cell"])
        points = series.get("observations") or series.get("points", [])
        axis_rows = {coordinate_to_tuple(p["period_cell"])[0] for p in points}
        first_value_col = min(coordinate_to_tuple(p["value_cell"])[1] for p in points)
    except (KeyError, TypeError, ValueError):
        return False, []
    cells = {}
    for region in sheet.get("business_facts", {}).get("table_regions", []):
        for row in region.get("rows", []):
            for cell in row:
                try:
                    cells[coordinate_to_tuple(cell["cell"])] = cell
                except (KeyError, TypeError, ValueError):
                    continue
    for axis_row in axis_rows:
        if axis_row >= label_row:
            continue
        for (row, col), cell in cells.items():
            if row != axis_row or col >= first_value_col or not _GEOGRAPHY.fullmatch(str(cell.get("value", "")).strip()):
                continue
            value = cells.get((label_row, col))
            if not value or (col != label_col and not _GEOGRAPHIC_KIND.fullmatch(str(value.get("value", "")).strip())):
                continue
            return True, [reference(sheet["name"], cell["cell"]), reference(sheet["name"], value["cell"])]
    return False, []
