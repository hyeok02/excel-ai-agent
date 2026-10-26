"""Source-aligned percentage observations; never infer a shared denominator by name."""
from decimal import Decimal
import re

from app.services.insights.display.percent_format import scales_by_percent
from app.services.insights.narratives.narrative_values import finite
from app.services.insights.narratives.table_schema import column


def share_rows(rows, header_index, schema, strict=True):
    label_role = "name" if "rank" in schema else "label"
    required = {label_role, "quantity", "share"}
    if not required <= schema.keys():
        return []
    result = []
    roles = required | ({"rank", "category"} if "rank" in schema else set())
    used = {position for role, position in schema.items() if role in roles}
    for cells in rows[header_index + 1:]:
        row = {column(cell): cell for cell in cells}
        if not any(position in row for position in used):
            continue
        label, quantity, share = (row.get(schema[role]) for role in
                                  (label_role, "quantity", "share"))
        if not label or not isinstance(label.get("value"), str):
            if strict:
                return []
            continue
        if not quantity or not share or not all(finite(cell.get("value"))
                                                for cell in (quantity, share)):
            if strict:
                return []
            continue
        name = " ".join(label["value"].split())
        if not name:
            return []
        if re.fullmatch(r"total|all|overall|합계|전체|총합", name, re.I):
            continue
        value, tolerance = percentage(share)
        amount = Decimal(str(quantity["value"]))
        if not 0 < value <= 100 or amount <= 0:
            if strict:
                return []
            continue
        rank = row.get(schema.get("rank"), {}).get("value")
        extras = tuple(sorted((key, str(cell.get("value", "")))
                              for key, cell in row.items() if key not in used))
        result.append({"name": name, "share": value, "quantity": amount,
                       "tolerance": tolerance, "rank": rank, "scope": extras,
                       "unit": re.sub(r"[0#., _()\-]", "", str(quantity.get("number_format") or "General")).casefold().replace("general", ""),
                       "cells": cells})
    if len({item["name"].casefold() for item in result}) != len(result):
        return []
    return result


def percentage(cell):
    value = Decimal(str(cell["value"]))
    fmt = str(cell.get("number_format") or "General")
    scale = Decimal(100) if scales_by_percent(fmt) else Decimal(1)
    precision = re.search(r"[0#]\.([0#]+)", fmt)
    places = len(precision[1]) if precision else max(0, -value.as_tuple().exponent)
    if fmt != "General" and not precision:
        places = 0
    uncertainty = Decimal(1).scaleb(-places) / 2
    return value * scale, uncertainty


def same_basis(items):
    if len(items) < 2 or len({(item["scope"], item["unit"]) for item in items}) != 1:
        return False
    # Display rounding defines an interval, not permission to mix arbitrary bases.
    lower, upper = Decimal(0), Decimal("Infinity")
    for item in items:
        value, error, amount = item["share"], item["tolerance"], item["quantity"]
        if value <= error:
            return False
        lower = max(lower, amount * 100 / (value + error))
        upper = min(upper, amount * 100 / (value - error))
    return lower <= upper
