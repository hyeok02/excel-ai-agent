"""Keep entity/category dimensions attached to ordinary row-oriented series."""
import re
from app.services.insights.display.display_quality import is_identifier_label
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.facts.fact_labels import resolve_fact_label
from app.services.insights.facts.series_scalars import scalar
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

_ANNOTATION = re.compile(r"^(?:notes?|comments?|remarks?|description|비고|메모|설명)$", re.I)


def numeric_columns(rows):
    return {_column(cell.get("address", "")) for row in rows for cell in row
            if scalar(_raw(cell))}


def complete_values(row, values, headers, schemas):
    """Preserve empty/error metric cells so a gap cannot disappear from a series."""
    present = {value["cell"] for value in values}
    missing = [{"cell": cell["address"], "label": resolve_fact_label(cell["address"], headers, schemas),
                "value": _raw(cell), "number_format": cell.get("number_format")}
               for cell in row if cell.get("address") not in present]
    return sorted([*values, *missing], key=lambda cell: column_index_from_string(_column(cell["cell"])))


def trend_values(values, metric_columns):
    values = [value for value in values if not _ANNOTATION.fullmatch(str(value.get("label") or "").strip())]
    dated = [value for value in values if date_value(value.get("value"))]
    if len(dated) != 1:
        return []
    dimensions = [value for value in values if value not in dated and (
        _column(value["cell"]) not in metric_columns or is_identifier_label(value.get("label"))
    )]
    # Missing/unnamed dimensions cannot prove that rows describe the same subject.
    if any(not value.get("label") or value.get("value") in (None, "") for value in dimensions):
        return []
    scope = " / ".join(f"{value['label']}={value['value']}" for value in dimensions)
    result = [dated[0]]
    for value in values:
        if value in dated or value in dimensions:
            continue
        label = str(value.get("label") or "")
        result.append({**value, "label": f"{scope} > {label}" if scope and label else label})
    return result


def _column(address):
    return coordinate_from_string(str(address))[0]


def _raw(cell):
    return cell.get("cached_value") if cell.get("formula") else cell.get("value")
