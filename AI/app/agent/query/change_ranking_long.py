"""Reuse complete conditional record grouping for ranked period changes."""
from dataclasses import replace
import re

from app.agent.query.comparison_scope import GROUP_ALIASES
from app.agent.query.grouped_trend_sources import grouped_sources
from app.agent.query.grouped_trend_series import grouped_series
from app.agent.query.trend_source_models import TrendCandidate


def long_ranking_series(question, summary, index, tables, group):
    aliases = GROUP_ALIASES.get(group, set())
    result = []
    for table in tables:
        groups = [column for column in table.columns if column.header.casefold().strip() in aliases]
        if len(groups) != 1:
            continue
        group_column = groups[0]
        # The ranked dimension is already requested, even without the suffix 별.
        escaped = table.sheet_name.replace("'", "''")
        translated = f"'{escaped}'!{table.reference} 범위 " + question + f" {group_column.header}별"
        sources, _ = grouped_sources(translated, summary, index)
        sources = [source for source in sources if source.table.id == table.id
                   and source.request.groups == (group_column.id,)]
        for source in sources:
            for _, candidate, units, evidence in grouped_series(source, index):
                labels = [cell for cell in candidate.observations[0].entity_cells
                          if re.match(r"[A-Z]+", cell.address)[0] == group_column.id
                          and cell.sheet_name == table.sheet_name]
                if len(labels) != 1:
                    raise ValueError("ambiguous_group_header")
                label = labels[0]
                points = tuple(replace(point, label=label,
                    context_cells=tuple(dict.fromkeys((*point.context_cells, point.label))),
                    entity_cells=tuple(cell for cell in point.entity_cells
                                       if re.match(r"[A-Z]+", cell.address)[0] != group_column.id))
                    for point in candidate.observations)
                candidate = replace(candidate, observations=points,
                                    context=tuple(dict.fromkeys((*candidate.context, *evidence))))
                result.append((candidate, units, source.request.residual))
    return result
