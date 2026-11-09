"""Group totals keep the unit their source column shows: $21,524.36, not 21,524.36."""
from app.agent.query.excel_number_formats import parse_number_format


def total_unit(table, measure):
    """(prefix, suffix) every numeric cell of the measure shows, or none when they differ or rescale."""
    if not measure:
        return "", ""
    styles = {row.number_formats.get(measure, "General") for row in table.rows
              if isinstance(row.values.get(measure), (int, float)) and not isinstance(row.values.get(measure), bool)}
    if len(styles) != 1:
        return "", ""
    spec = parse_number_format(next(iter(styles)))
    if spec.percent or spec.multiplier != 1 or spec.divisor != 1:
        return "", ""
    return spec.prefix, spec.suffix


def shown_total(value, unit=("", "")):
    value = float(value)
    text = f"{abs(value):,.0f}" if value.is_integer() else f"{abs(value):,.2f}"
    return f"{'-' if value < 0 else ''}{unit[0]}{text}{unit[1]}"
