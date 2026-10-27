"""Expose source headers and bounded samples for schema-grounded query planning."""
import re
from dataclasses import replace

from app.agent.query.tabular_catalog_models import QueryTable
from app.agent.query.tabular_catalog_sources import source_cells, table_context, table_sources
from app.agent.query.tabular_catalog_builder import build_table as _build_table
from app.agent.query.column_context import column_context
from app.agent.query.tabular_header_paths import column_header_path
from app.agent.query.tabular_catalog_ranking import table_relevance as _relevance
from app.agent.query.tabular_catalog_projection import range_matches, ranked_columns, source_matches

MAX_CATALOG_TABLES = 18
MAX_CATALOG_COLUMNS = 80
MAX_CATALOG_CHARACTERS = 30_000
MAX_TABLE_CHARACTERS = 12_000


def build_query_tables(summary) -> list[QueryTable]:
    tables = []
    for sheet in summary.sheets:
        sheet_cells = {address: cell for region in sheet.regions
                       for address, cell in source_cells(region).items()}
        hidden_columns = frozenset(column for region in sheet.regions for column in region.hidden_columns)
        parents = tuple(span for region in sheet.regions for span in region.merged_ranges)
        for reference, cells, complete, merged, hidden, kind in table_sources(sheet):
            table = _build_table(sheet.name, reference, cells, complete, merged, hidden)
            if table is not None:
                columns = tuple(replace(column, context=column_context(sheet.name, column, sheet_cells, parents, reference),
                                        header_path=column_header_path(sheet.name, column, sheet_cells, parents, reference))
                                for column in table.columns)
                tables.append(replace(table, columns=columns, source_kind=kind, context=table_context(sheet.name, reference, sheet_cells),
                                      hidden_columns=hidden_columns & {c.id for c in table.columns}))
    return tables


def query_catalog(summary, question: str) -> list[dict]:
    tables = build_query_tables(summary)
    tokens = set(re.findall(r"[\w]+", question.casefold()))
    tables.sort(key=lambda table: (table.sheet_name.casefold() not in question.casefold(),
                                  not range_matches(table, question),
                                  -_relevance(table, tokens)))
    catalog, size = [], 0
    for table in tables[:MAX_CATALOG_TABLES]:
        columns = ranked_columns(table, question, tokens)[:MAX_CATALOG_COLUMNS]
        entry = {
            "table_id": table.id, "sheet_name": table.sheet_name,
            "range": table.reference, "complete": table.complete,
            "row_count": len(table.rows) if table.complete else None,
            "sampled_row_count": len(table.rows),
            "excluded_row_count": len(table.excluded_rows),
            "metadata_row_count": len(table.metadata_rows),
            "column_count": len(table.columns),
            "context": [{"reference": reference, "text": value}
                        for reference, value in table.context],
            "columns": [{
                "column_id": column.id, "header": column.header,
                "header_reference": column.header_reference,
                "parent_context": list(column.context),
                "header_path": list(column.header_path),
                "qualified_header": column.display_header,
                "source_identifiers": list(column.source_identifiers),
                "hidden": column.id in table.hidden_columns,
                "samples": list(column.sample_values),
            } for column in columns],
        }
        # A wide source must not disappear because its first 80 labels exceed
        # the prompt budget. Keep its identity axis and best-matching columns.
        budget = min(MAX_TABLE_CHARACTERS, MAX_CATALOG_CHARACTERS - size)
        while len(str(entry)) > max(2_000, budget - 2_000) and len(entry["columns"]) > 2:
            entry["columns"].pop()
            columns.pop()
        entry["omitted_column_count"] = len(table.columns) - len(columns)
        matched = source_matches(table, columns, question)
        if len(str(entry)) + len(str(matched)) < budget:
            entry["matching_source_rows"] = matched
        positions = {column.id: position for position, column in enumerate(table.columns)}
        entry["columns"].sort(key=lambda column: positions[column["column_id"]])
        entry_size = len(str(entry))
        if size + entry_size > MAX_CATALOG_CHARACTERS:
            continue
        catalog.append(entry)
        size += entry_size
    return catalog
