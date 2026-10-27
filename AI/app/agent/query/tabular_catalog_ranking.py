"""Order source catalogs by request vocabulary without changing their meaning."""


def table_relevance(table, tokens):
    source = " ".join([table.sheet_name] + [column.display_header for column in table.columns])
    source += " " + " ".join(value for _, value in table.context)
    source += " " + " ".join(str(value) for column in table.columns
                             for value in column.sample_values if value is not None)
    source += " " + " ".join(value for column in table.columns for _, value in column.source_identifiers)
    relevance = sum(len(token) for token in tokens if len(token) > 1 and token in source.casefold())
    # Hidden helper dictionaries stay addressable without displacing equally
    # relevant visible report populations.
    return relevance - (10 if len(table.hidden_columns) == len(table.columns) else 0)
