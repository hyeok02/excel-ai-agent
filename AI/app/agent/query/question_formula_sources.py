"""Ephemeral calculation view: never rewrite an uploaded workbook or its index."""
from dataclasses import dataclass, replace

from app.agent.query.formula_resolution import FormulaResolver


@dataclass(frozen=True)
class QuestionFormulaSources:
    summary: object
    index: object
    original_index: object
    resolutions: dict


def prepare_formula_sources(summary, index):
    resolutions = {item.reference: item for item in FormulaResolver(index).resolve_all()}
    recovered = {key: item for key, item in resolutions.items() if item.status == "recovered"}
    if not recovered:
        return QuestionFormulaSources(summary, index, index, resolutions)
    rows = tuple(replace(row, cells=tuple(
        replace(cell, value=recovered[cell.reference].value)
        if cell.reference in recovered else cell for cell in row.cells
    )) for row in index.rows)
    if summary is None:
        return QuestionFormulaSources(None, replace(index, rows=rows), index, resolutions)
    sheets = []
    for sheet in summary.sheets:
        regions = [replace(region,
            analysis_rows=_dict_rows(region.analysis_rows, sheet.name, recovered),
            query_rows=_dict_rows(region.query_rows, sheet.name, recovered),
            preview_rows=_snapshots(region.preview_rows, sheet.name, recovered),
        ) for region in sheet.regions]
        tables = [replace(table, preview_rows=_snapshots(table.preview_rows, sheet.name, recovered))
                  for table in sheet.tables]
        sheets.append(replace(sheet, regions=regions, tables=tables))
    return QuestionFormulaSources(replace(summary, sheets=sheets), replace(index, rows=rows), index, resolutions)


def _dict_rows(rows, sheet, recovered):
    return [[dict(cell, cached_value=recovered[f"{sheet}!{cell['address']}"].value)
             if cell.get("formula") and f"{sheet}!{cell['address']}" in recovered else dict(cell)
             for cell in row] for row in rows]


def _snapshots(rows, sheet, recovered):
    return [[replace(cell, cached_value=recovered[f"{sheet}!{cell.address}"].value)
             if cell.formula and f"{sheet}!{cell.address}" in recovered else cell
             for cell in row] for row in rows]
