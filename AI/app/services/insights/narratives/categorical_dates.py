"""Date spread of a record table, cited against the range that was counted."""
from app.services.insights.facts.categorical_columns import date_column
from app.services.insights.display.glossary import readable
from app.services.insights.narratives.narrative_values import (
    insight, number, period, reference,
)
from app.services.insights.narratives.topic_labels import source_topic


def counted_range(sheet, cells):
    """Cite the counted range itself: a count of 18 must not point at 10 cells."""
    if not cells:
        return []
    span = cells[0]["cell"]
    if len(cells) > 1:
        span = f"{span}:{cells[-1]['cell']}"
    return [reference(sheet, span)]


def date_spread(sheet, header, records):
    found = date_column(header, records)
    if not found:
        return None
    name, ordered, counts, cells = found
    peak_value, peak_count = counts[0]
    span = (f"{period(ordered[0])}부터 {period(ordered[-1])}까지"
            if ordered[0] != ordered[-1] else period(ordered[0]))
    detail = (f" 가장 많은 날은 {period(peak_value)}로 {number(peak_count)}건입니다."
              if peak_count > 1 else "")
    return insight(
        f"{readable(name)} 분포",
        f"기록은 {span} 모두 {number(len(counts))}개 시점에 걸쳐 있습니다.{detail}",
        [*([reference(sheet, cell["cell"]) for cell in header
            if _flat(cell.get("value")) == _flat(name)][:1]),
         *counted_range(sheet, cells)], topic=source_topic(name),
    )


def _flat(value):
    return " ".join(str(value or "").split())
