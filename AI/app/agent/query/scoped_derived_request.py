"""Keep source headers and category literals out of mathematical grammar."""
import re

from app.agent.query.derived_trend_request import calculation_question, GROWTH, SHARE, YOY, MOM, PREVIOUS
from app.agent.query.grouped_share_trend_request import protect_headers, restore_headers
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.trend_labels import trend_metric_label_matches
from app.agent.query.trend_source_readback import table_rows


def _protect_values(question, values):
    replacements = {}
    for value in sorted(set(values), key=len, reverse=True):
        matches = value_matches(question, value)
        if not matches:
            continue
        marker = f"__category{len(replacements)}__"
        for match in reversed(matches):
            question = question[:match.start()] + marker + question[match.end():]
        replacements[marker] = value
    return question, replacements


def clean_scoped_question(question, tables, index):
    question, sources = _protect_source_names(question, (table.sheet_name for table in tables))
    masked, fields = protect_headers(question, tables)
    values = []
    for table in tables:
        if not any(trend_metric_label_matches(column.header, question) for column in table.columns):
            continue
        rows, error = table_rows(table, tables, index, question)
        if error:
            continue  # The actual bound source adapter rejects incomplete data.
        header_addresses = {column.header_reference for column in table.columns}
        values.extend(cell.value for row in rows for cell in row.cells
                      if cell.address not in header_addresses and isinstance(cell.value, str)
                      and cell.value.strip() and source_period(cell.value) is None)
    masked, values = _protect_values(masked, values)
    clean = re.sub(r"안에서|내에서", "에서", calculation_question(masked))
    return restore_headers(restore_headers(restore_headers(clean, values), fields), sources), masked


def source_operation(question, source):
    question, _ = _protect_source_names(question, (source.table.sheet_name,))
    masked, _ = protect_headers(question, [source.table])
    masked, _ = _protect_values(masked, [item.value for item in source.request.filters if isinstance(item.value, str)])
    return masked


def _protect_source_names(question, names):
    replacements = {}
    for name in sorted(set(names), key=len, reverse=True):
        matches = value_matches(question, name)
        for match in reversed(matches):
            before, after = question[:match.start()], question[match.end():]
            qualified = (re.search(r"(?:시트|\bsheet)\s*['‘“\"]?\s*$", before, re.I)
                         or re.match(r"['’”\"]?\s*(?:시트|sheet\b|!)", after, re.I)
                         or (before.endswith(("'", '"', "‘", "“")) and after.startswith(("'", '"', "’", "”"))))
            # An unqualified temporal word can still be a real rate baseline.
            if not qualified and any(pattern.search(name) for pattern in (GROWTH, SHARE, YOY, MOM, PREVIOUS)):
                continue
            marker = f"__source{len(replacements)}__"
            question = question[:match.start()] + marker + question[match.end():]
            replacements[marker] = name
    return question, replacements
