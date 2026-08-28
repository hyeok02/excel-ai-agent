from collections.abc import Iterable


def build_content_outline(
    sheet_data: dict[str, object],
    regions: list[dict[str, object]],
    column_schemas: list[dict[str, object]],
    tables: list[dict[str, object]],
    charts: list[dict[str, object]],
) -> dict[str, object]:
    classification = sheet_data.get("sheet_classification") or {}
    if not isinstance(classification, dict):
        classification = {}
    reasons = classification.get("reasons") or []
    return {
        "sheet_role": classification.get("role"),
        "role_reasons": _reason_messages(reasons),
        "region_titles": _unique(
            region.get("title") for region in regions if region.get("title")
        )[:6],
        "header_labels": _header_labels(regions)[:18],
        "columns": [
            {
                "name": schema.get("display_name"),
                "header_path": schema.get("header_path", []),
                "standard_field": schema.get("standard_field"),
                "data_type": schema.get("data_type"),
                "unit": schema.get("unit_label") or schema.get("unit_type"),
            }
            for schema in column_schemas[:18]
        ],
        "table_headers": _unique(
            header for table in tables for header in table.get("headers", [])
        )[:18],
        "chart_titles": _unique(
            chart.get("title") for chart in charts if chart.get("title")
        )[:6],
    }


def _reason_messages(reasons: object) -> list[str]:
    if not isinstance(reasons, (list, tuple)):
        return []
    return [
        str(reason["message"])
        for reason in reasons[:4]
        if isinstance(reason, dict) and reason.get("message")
    ]


def _header_labels(regions: list[dict[str, object]]) -> list[str]:
    labels = []
    for region in regions:
        for path in region.get("header_paths", []):
            if isinstance(path, dict):
                labels.extend(str(label) for label in path.get("labels", []) if label)
    return _unique(labels)


def _unique(values: Iterable[object]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value).strip()
        normalized = text.casefold()
        if not text or normalized in seen:
            continue
        seen.add(normalized)
        result.append(text)
    return result
