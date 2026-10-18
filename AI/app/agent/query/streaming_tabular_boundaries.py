"""Fail closed when a source rectangle mixes records with another population."""
import re


_TOTAL_LABEL = re.compile(
    r"\b(?:sub[\s-]?total|grand[\s-]+total|total)\b|"
    r"(?<![가-힣])(?:소계|총계|합계|누계|총합)(?![가-힣])", re.I,
)
_TOTAL_FORMULA = re.compile(r"(?<!\w)(?:_xlfn\.)?(?:SUBTOTAL|AGGREGATE)\s*\(", re.I)


def ambiguous_boundary(row, table, numeric_columns):
    values = [row.values[column.id] for column in table.columns]
    aligned = sum(isinstance(value, str) and value.strip() == column.header
                  for column, value in zip(table.columns, values))
    threshold = max(1 if len(values) == 2 else 2, (len(values) + 1) // 2)
    if len(values) > 1 and aligned >= threshold and all(
        value is None or isinstance(value, str) for value in values
    ):
        return True
    # Native table totals are explicit metadata. An inferred rectangle has no
    # equivalent guarantee: do not silently count a subtotal or drop it by guess.
    if table.source_kind != "native":
        if (any(isinstance(value, str) and _TOTAL_LABEL.search(value) for value in values)
                or any(_TOTAL_FORMULA.search(formula) for formula in row.formulas.values())):
            return True
        if (all(value is None or isinstance(value, str) for value in values)
                and any(isinstance(row.values[column], str) and row.values[column].strip()
                        for column in numeric_columns)):
            return True  # A new textual header may use entirely different labels.
    numeric_columns.update(column for column, value in row.values.items()
                           if isinstance(value, (int, float)) and not isinstance(value, bool))
    return False
