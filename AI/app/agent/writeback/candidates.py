import re

from app.agent.query.index import IndexedCell, WorkbookDataIndex
from app.agent.query.search_terms import relevance, search_terms
from app.agent.writeback.value_authorization import as_number
from app.services.insights.verification.numeric_validation import numbers

MAX_CANDIDATE_CELLS = 240
MAX_TEXT_ANCHORS = 12
MAX_VALUE_ANCHORS = 8


def select_writeback_candidates(
    instruction: str, index: WorkbookDataIndex
) -> list[IndexedCell]:
    value_positions, value_cells = _stated_value_matches(instruction, index)
    anchors = list(
        dict.fromkeys([*value_positions, *_text_anchors(instruction, index)])
    )
    direct_references = set(re.findall(r"\b[A-Za-z]{1,3}[1-9][0-9]{0,6}\b", instruction))
    mentioned_sheets = {
        row.sheet_name for row in index.rows if row.sheet_name.casefold() in instruction.casefold()
    }
    selected_positions = _neighbor_positions(index, anchors)
    cells = [
        cell
        for position in selected_positions
        for cell in index.rows[position].cells
    ]
    direct = [
        cell
        for row in index.rows
        for cell in row.cells
        if cell.address.upper() in {item.upper() for item in direct_references}
        and (not mentioned_sheets or cell.sheet_name in mentioned_sheets)
    ]
    if not cells:
        dense_rows = sorted(index.rows, key=lambda row: len(row.cells), reverse=True)[:40]
        cells = [cell for row in dense_rows for cell in row.cells]
    # 요청에 적힌 값을 그대로 들고 있는 셀은 상한에 밀려 잘리지 않도록 앞에 둔다.
    ordered = [*direct, *value_cells, *cells]
    return list({cell.reference: cell for cell in ordered}.values())[:MAX_CANDIDATE_CELLS]


def _stated_value_matches(
    instruction: str, index: WorkbookDataIndex
) -> tuple[list[int], list[IndexedCell]]:
    """
    요청에 적힌 숫자를 실제 값으로 들고 있는 행과 셀.

    "1081에서 981로"처럼 바꾸기 전 값을 말했다면 그 값을 가진 셀이 대상일 가능성이 가장 높다.
    본문 검색은 행 전체를 문자열로 훑어 11081 같은 값도 걸리지만, 여기서는 숫자로 비교한다.
    """
    stated = numbers(instruction)
    if not stated:
        return [], []
    positions: list[int] = []
    cells: list[IndexedCell] = []
    for position, row in enumerate(index.rows):
        matched = [cell for cell in row.cells if as_number(cell.value) in stated]
        if matched:
            positions.append(position)
            cells.extend(matched)
            if len(positions) >= MAX_VALUE_ANCHORS:
                break
    return positions, cells


def _text_anchors(instruction: str, index: WorkbookDataIndex) -> list[int]:
    terms = search_terms(instruction)
    scored = [
        (relevance(row, terms), position)
        for position, row in enumerate(index.rows)
    ]
    return [
        position
        for score, position in sorted(scored, key=lambda item: (-item[0], item[1]))
        if score > 0
    ][:MAX_TEXT_ANCHORS]


def _neighbor_positions(index: WorkbookDataIndex, anchors: list[int]) -> list[int]:
    """
    앵커 우선순위를 유지한다.

    시트 위치 순으로 정렬하면 앞쪽의 넓은 시트가 후보 수 상한을 다 써버려,
    뒤쪽 시트에 있는 정답 셀이 모델에게 아예 전달되지 않는다.
    """
    selected: list[int] = []
    seen: set[int] = set()
    for anchor in anchors:
        sheet_name = index.rows[anchor].sheet_name
        for position in range(max(0, anchor - 4), min(len(index.rows), anchor + 10)):
            if index.rows[position].sheet_name == sheet_name and position not in seen:
                seen.add(position)
                selected.append(position)
    return selected
