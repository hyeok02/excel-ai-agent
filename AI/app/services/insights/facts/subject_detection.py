"""Find the workbook's subject where a sheet writes it down, never by guessing.

Some workbooks name the company in a labelled row; others repeat it as the
header spanning every period column of each sheet. Both are written in the
file, so both may be cited. A filename is not a source and is never read here.
"""
from app.services.insights.narratives.narrative_values import reference
from app.services.insights.narratives.table_dates import column as col
from app.services.insights.facts.table_inputs import narrative_regions

MIN_SPAN = 3
MIN_SHEETS = 2
MIN_LENGTH = 4
MAX_LENGTH = 80
# 영역 제목은 표 머리에 한 칸으로 적힌다. IBM 자료에서 회사 이름은 B4 한 칸
# 뿐이라 '3칸 이상 반복'을 요구하는 띠 탐지에 걸리지 않았고, 아래쪽 각주 띠인
# 'U.S. GAAP'이 여러 시트에 반복된다는 이유로 주어 자리를 가져갔다.
TOP_ROWS = 12
TITLE_WORDS = 2


def spanning_subject(context) -> tuple[str, list[str]]:
    """A name repeated as a table header across sheets is what the file is about.

    Requiring two sheets keeps single-table wording such as a period label out.
    Among the survivors the longest is taken: a workbook usually carries both a
    ticker and a full name, and the full name is the one a reader can use.
    """
    ranked = spanning_subjects(context)
    return (ranked[0][0], ranked[0][1][:1]) if ranked else ("", [])


def spanning_subjects(context) -> list[tuple[str, list[str]]]:
    """Return every repeated source subject so locality can choose among them.

    표 머리에 적힌 영역 제목을 먼저 내놓는다. 한 시트에만 있어도 제목은 그
    표가 무엇에 대한 것인지를 적어 둔 자리다. 본문 띠는 종전대로 두 시트
    이상에서 되풀이될 때만 받는다.
    """
    return [*_title_subjects(context), *_body_subjects(context)]


def _title_subjects(context) -> list[tuple[str, list[str]]]:
    found: dict[str, list[str]] = {}
    for sheet in context.get("sheets", []):
        if not isinstance(sheet, dict):
            continue
        name = str(sheet.get("name", ""))
        for region in narrative_regions(sheet.get("business_facts", {})):
            title = " ".join(str(region.get("title") or "").split())
            cell = _title_cell(region, title)
            if cell and _looks_titled(title) and _near_the_top(cell):
                found.setdefault(title, [reference(name, cell)])
    return list(found.items())


def _title_cell(region, title) -> str:
    if not title:
        return ""
    for row in region.get("rows", []):
        for cell in row:
            if " ".join(str(cell.get("value", "")).split()) == title:
                return str(cell.get("cell", ""))
    return ""


def _looks_titled(title: str) -> bool:
    return (
        MIN_LENGTH <= len(title) <= MAX_LENGTH
        and len(title.split()) >= TITLE_WORDS
        and not title.endswith(":")
    )


def _near_the_top(cell: str) -> bool:
    digits = "".join(character for character in cell if character.isdigit())
    return bool(digits) and int(digits) <= TOP_ROWS


def _body_subjects(context) -> list[tuple[str, list[str]]]:
    found: dict[str, list] = {}
    for sheet in context.get("sheets", []):
        if not isinstance(sheet, dict):
            continue
        name = str(sheet.get("name", ""))
        for value, cell in _spans(sheet):
            entry = found.setdefault(value, [set(), []])
            entry[0].add(name)
            cited = reference(name, cell)
            if cited not in entry[1]:
                entry[1].append(cited)
    return sorted(
        ((value, entry[1]) for value, entry in found.items()
         if len(entry[0]) >= MIN_SHEETS),
        key=lambda item: len(item[0]),
        reverse=True,
    )


def _spans(sheet):
    for region in narrative_regions(sheet.get("business_facts", {})):
        for row in region.get("rows", []):
            yield from _row_spans(row)


def _row_spans(row):
    cells = [cell for cell in row if isinstance(cell.get("value"), str)]
    index = 0
    while index < len(cells):
        end = index
        while (end + 1 < len(cells)
               and cells[end + 1]["value"] == cells[index]["value"]
               and col(cells[end + 1]) == col(cells[end]) + 1):
            end += 1
        text = " ".join(str(cells[index]["value"]).split())
        if end - index + 1 >= MIN_SPAN and MIN_LENGTH <= len(text) <= MAX_LENGTH:
            yield text, cells[index]["cell"]
        index = end + 1
