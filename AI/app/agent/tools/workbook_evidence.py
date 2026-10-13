"""비교 답변이 근거로 드는 셀을 빠짐없이 모은다."""
from app.agent.tools.workbook_headers import evidence_with_header


def missing_reference_evidence(priority, present, rows, headers):
    seen = {f"{item.sheet_name}!{item.reference}" for item in present}
    wanted = {reference for reference in priority if reference not in seen}
    return [
        evidence_with_header(row, cell, headers)
        for row in rows
        for cell in row.cells
        if cell.reference in wanted
    ]


def comparison_reference_order(
    comparison: dict[str, object] | None,
) -> dict[str, int]:
    if not comparison:
        return {}
    references = {
        reference: index
        for index, key in enumerate(("start_reference", "end_reference"))
        if isinstance((reference := comparison.get(key)), str)
    }
    groups = (
        comparison.get("ranked_changes"),
        comparison.get("largest_absolute_changes"),
        comparison.get("metrics"),
    )
    for metrics in groups:
        if not isinstance(metrics, list):
            continue
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            for key in ("start_reference", "end_reference"):
                reference = metric.get(key)
                if isinstance(reference, str) and reference not in references:
                    references[reference] = len(references)
            # 비교 답변은 항목 이름이 적힌 헤더 셀도 근거로 요구한다.
            for reference in metric.get("header_references") or ():
                if isinstance(reference, str) and reference not in references:
                    references[reference] = len(references)
    return references
