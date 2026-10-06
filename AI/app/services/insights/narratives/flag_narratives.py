"""Describe a checklist by what each check column says, blanks included."""
from app.services.insights.facts.categorical_headers import header_index
from app.services.insights.facts.flag_columns import blank_records, flag_matrix
from app.services.insights.narratives.checklist_subject import (
    check_names, stalled_check, subject_of,
)
from app.services.insights.display.glossary import readable
from app.services.insights.narratives.categorical_dates import counted_range
from app.services.insights.narratives.narrative_values import (
    insight, number, reference, topic_particle,
)
from app.services.insights.narratives.topic_labels import source_topic
from app.services.insights.facts.sheet_scope import narrative_sheet_groups
from app.services.insights.facts.table_inputs import narrative_regions

MIN_RECORDS = 4
MAX_COLUMN_ITEMS = 4


def flag_matrix_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    for sheets in (primary, comparisons):
        for _, sheet in sheets:
            found = _sheet_report(str(sheet.get("name", "")), sheet)
            if found:
                return found
    return [], ""


def _sheet_report(name, sheet):
    for region in narrative_regions(sheet.get("business_facts", {})):
        rows = region.get("rows", [])
        index = header_index(rows)
        if index is None:
            continue
        header, records = rows[index], rows[index + 1:]
        if len(records) < MIN_RECORDS:
            continue
        found = flag_matrix(header, records)
        if not found:
            continue
        items = _items(name, header, records, *found)
        if items:
            return items[:5], _overview(items)
    return None


def _overview(items):
    """The lead already says what the checklist is; add a check it has not named."""
    rest = items[0].fact.split("니다.", 1)[1].strip()
    following = next(
        (item.fact for item in items[1:]
         if item.title.rsplit(" 표시", 1)[0] not in items[0].fact),
        "",
    )
    return " ".join(part for part in (rest, following) if part)


def _items(sheet, header, records, label, run):
    subject = subject_of(label, records)
    blanks = blank_records(records, run)
    checked = len(records) - len(blanks)
    state = (f" {number(checked)}건이 점검됐고 {number(len(blanks))}건은 "
             "아직 아무 항목도 표시되지 않았습니다.") if blanks else ""
    cited = [reference(sheet, cell["cell"]) for _, cell, _, _ in run]
    if label:
        cited.insert(0, reference(sheet, label["cell"]))
    head = insight(
        f"{subject} 점검 현황",
        f"{subject} {number(len(records))}건을 {check_names(run)} 항목으로 "
        f"점검한 표입니다.{state} {stalled_check(run)}".rstrip(),
        cited, topic=source_topic(subject),
    )
    return [head, *_columns(sheet, records, run)]


def _columns(sheet, records, run):
    ordered = sorted(run, key=lambda found: -len(found[2]))
    items = []
    for _, cell, counts, filled in ordered[:MAX_COLUMN_ITEMS]:
        name = readable(cell["value"])
        marks = ", ".join(f"{mark} {number(count)}건"
                          for mark, count in counts.most_common())
        missing = len(records) - len(filled)
        tail = f"이고, {number(missing)}건은 비어 있습니다" if missing else "입니다"
        items.append(insight(
            f"{name} 표시",
            f"‘{name}’{topic_particle(name)} 기재된 "
            f"{number(len(filled))}건이 {marks}{tail}.",
            [reference(sheet, cell["cell"]), *counted_range(sheet, filled)],
            topic=source_topic(name),
        ))
    return items


def checklist_lead(report):
    """Reuse the checklist's own first sentence as the workbook's lead."""
    head = next((item for item in report.insights
                 if item.title.endswith(" 점검 현황")), None)
    if head is None or "니다." not in head.fact:
        return ""
    return f"이 파일은 {head.fact.split('니다.', 1)[0]}니다."
