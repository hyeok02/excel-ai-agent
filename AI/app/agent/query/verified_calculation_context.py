"""Build explicit calculations from deterministic workbook facts."""


def fact_calculations(
    context: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, str]]:
    calculations: list[dict[str, object]] = []
    descriptions: dict[str, str] = {}
    for sheet in context.get("sheets", []):
        if not isinstance(sheet, dict):
            continue
        name = str(sheet.get("name", ""))
        facts = sheet.get("business_facts", {})
        comparison = facts.get("comparable_transactions")
        if isinstance(comparison, dict):
            calculations.extend(
                _comparable(name, comparison, descriptions)
            )
        calculations.extend(
            _horizontal(name, facts.get("horizontal_series"), descriptions)
        )
    return calculations, descriptions


def comparable_count_specs(context: dict[str, object]) -> list[dict[str, object]]:
    specs = []
    for sheet in context.get("sheets", []):
        if not isinstance(sheet, dict):
            continue
        comparison = sheet.get("business_facts", {}).get("comparable_transactions")
        if not isinstance(comparison, dict):
            continue
        for metric in comparison.get("metrics", []):
            if isinstance(metric, dict) and metric.get("peer_range"):
                specs.append(
                    {
                        "range": metric["peer_range"],
                        "label": metric.get("label") or metric.get("kind"),
                        "valid_count": metric.get("valid_count"),
                        "peer_count": metric.get("peer_count"),
                    }
                )
    return specs


def _comparable(sheet, comparison, descriptions):
    calculations = []
    subject = str(comparison.get("subject") or "분석 대상")
    subject_cell = comparison.get("subject_cell")
    if subject_cell:
        descriptions[_reference(sheet, subject_cell)] = "분석 대상 거래"
    for metric in comparison.get("metrics", []):
        if not isinstance(metric, dict) or not metric.get("median_cell"):
            continue
        median_ref = _reference(sheet, metric["median_cell"])
        subject_ref = _reference(sheet, metric["subject_cell"])
        label = str(metric.get("label") or metric.get("kind") or "거래 지표")
        descriptions[median_ref] = f"{label} 비교거래 중앙값"
        descriptions[subject_ref] = f"{subject} {label}"
        unit = "multiple" if metric.get("kind") == "ebitda_multiple" else "source_unit"
        common = _operands(
            label,
            [median_ref, subject_ref],
            [metric["median"], metric["subject_value"]],
        )
        calculations.extend(
            [
                _calculation(common, "difference", metric["difference"], unit),
                _calculation(
                    common, "percent_change", metric["difference_percent"], "percent"
                ),
            ]
        )
    return calculations


def _horizontal(sheet, series_list, descriptions):
    calculations = []
    for series in series_list if isinstance(series_list, list) else []:
        points = series.get("points") if isinstance(series, dict) else None
        if not isinstance(points, list) or len(points) < 2:
            continue
        start, end = points[0], points[-1]
        if not _number(start.get("value")) or not _number(end.get("value")):
            continue
        label = str(series.get("metric") or "지표")
        refs = [
            _reference(sheet, start.get("value_cell")),
            _reference(sheet, end.get("value_cell")),
        ]
        values = [start["value"], end["value"]]
        common = _operands(label, refs, values)
        change = float(values[1]) - float(values[0])
        percent_series = all("%" in str(point.get("number_format", "")) for point in points)
        calculations.append(
            _calculation(common, "difference", change, "percent" if percent_series else "source_unit")
        )
        if not percent_series and float(values[0]) != 0:
            rate = change / abs(float(values[0])) * 100
            calculations.append(_calculation(common, "percent_change", rate, "percent"))
        _describe_horizontal(sheet, series, start, end, descriptions)
    return calculations


def _describe_horizontal(sheet, series, start, end, descriptions):
    label = str(series.get("metric") or "지표")
    for cell in (series.get("label_cell"), series.get("scope_cell")):
        if cell:
            descriptions[_reference(sheet, cell)] = label
    for point, prefix in ((start, "시작"), (end, "종료")):
        descriptions[_reference(sheet, point.get("period_cell"))] = f"{label} {prefix} 시점"
        descriptions[_reference(sheet, point.get("value_cell"))] = f"{label} {prefix} 값"


def _operands(label, references, values):
    return {
        "operand_references": references,
        "operand_values": values,
        "label": label,
    }


def _calculation(common, operation, result, unit):
    return {**common, "operation": operation, "result": result, "unit": unit}


def _reference(sheet, cell):
    return f"{sheet}!{cell}"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
