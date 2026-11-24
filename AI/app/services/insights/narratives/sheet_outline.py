"""What a sheet holds when no figure can be read from it: a large table's columns, or a form's sections.

Said only when no other narrative found anything, so a file never comes back with nothing at all.
"""
import re

from app.services.insights.facts.sheet_scope import narrative_sheet_groups
from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.narrative_values import finite, insight, number, reference

_SECTION = re.compile(r"^\s*(?:[①-⑳]\s*\S|\d{1,2}[.)]\s*[^\d\s])")
_SPACED = re.compile(r"(?<=[가-힣]) (?=[가-힣](?:\s|$|[(]))")  # '시 료 채 취' is 시료채취 written apart
_SHOWN = 6


def outline_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    for _, sheet in primary or comparisons:
        items = [form] if (form := _form(sheet)) else _large_table(sheet)  # a large one: its totals too
        if items:
            return items, " ".join(item.fact for item in items[:2])
    return [], ""


def _large_table(sheet):
    """A sheet of many rows that no narrative read: its size and its columns."""
    facts = sheet.get("business_facts", {})
    if (sheet.get("rows") or 0) < 30:
        return []  # a small sheet is read cell by cell elsewhere
    schemas = [schema for schema in facts.get("all_column_schemas") or sheet.get("column_schema_samples", [])
               if schema.get("display_name") and schema.get("data_type") != "empty"]
    if not schemas:
        return []
    top = re.search(r"\d+", str(schemas[0].get("source_range", "")))
    if not top:
        return []
    name = str(sheet.get("name", ""))
    present = {cell.get("cell"): cell for region in narrative_regions(facts) for row in region.get("rows", [])
               for cell in row}
    schemas = [schema for schema in schemas if f"{schema['column']}{top[0]}" in present  # its header is read
               and " ".join(str(present[f"{schema['column']}{top[0]}"].get("value") or "").split())
               == " ".join(str(schema["display_name"]).split())]
    if len(schemas) < 2:
        return []
    shown = [str(schema["display_name"]).strip() for schema in schemas[:_SHOWN]]
    fact = (f"‘{name}’ 시트에는 {number(sheet.get('rows') or 0)}행 {number(sheet.get('columns') or 0)}열 규모의 표가 있습니다. "
            f"열은 {', '.join(shown)} 등입니다.")
    cited = [reference(name, f"{schema['column']}{top[0]}") for schema in schemas[:_SHOWN]]
    from app.services.insights.narratives.large_tables import large_table_insights
    return [insight(f"{name} 시트 구성", fact, cited, "summary", topic=name),
            *large_table_insights(sheet, [(schema["column"], str(schema["display_name"]).strip()) for schema in schemas],
                                  int(top[0]))]


def _form(sheet):
    """A sheet of labels with almost no numbers entered: an input form, read by its numbered sections."""
    cells = [cell for region in narrative_regions(sheet.get("business_facts", {}))
             for row in region.get("rows", []) for cell in row if cell.get("value") not in (None, "")]
    numeric = sum(finite(cell.get("value")) and cell["value"] != 0 for cell in cells)  # a blank form's formulas show 0
    if len(cells) < 20 or numeric > len(cells) * 0.1:
        return None
    sections = [cell for cell in cells if isinstance(cell.get("value"), str) and _SECTION.match(cell["value"])]
    shown = list(dict.fromkeys(_SPACED.sub("", " ".join(cell["value"].split())) for cell in sections))
    if len(shown) < 2:
        return None
    name = str(sheet.get("name", ""))
    fact = (f"‘{name}’ 시트는 값을 채워 넣는 서식으로, 숫자가 거의 입력되어 있지 않습니다. "
            f"{', '.join(shown[:_SHOWN])} 등 {len(shown)}개 항목으로 구성돼 있습니다.")
    cited = [reference(name, cell["cell"]) for cell in sections[:_SHOWN]]
    return insight(f"{name} 서식 구성", fact, cited, "summary", topic=name)
