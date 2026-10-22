"""Constrain ordinary row/column requests using labels actually in the workbook."""
import re

from app.agent.writeback.references import column_number
from app.agent.writeback.target_syntax import sheet_mentions


def semantic_target_risk(cell, instruction, index, headers) -> str | None:
    sheets = {row.sheet_name for row in index.rows}
    named = {name for _, _, name in sheet_mentions(instruction, sheets)}
    if named and cell.sheet_name not in named:
        return "요청에 명시한 시트와 변경 대상 시트가 다릅니다."
    # Values after the assignment particle describe replacements, not source labels.
    prefix = re.split(r"(?:을|를)\s+", instruction, maxsplit=1)[0]
    folded = re.sub(r"\s+", "", prefix).casefold()
    row_numbers, columns = set(), set()
    matching_sheets = set()
    for row in index.rows:
        known = headers.header_rows.get(row.sheet_name, set())
        data_row = row.row_number not in known if known else any(
            isinstance(item.value, (int, float)) or item.formula for item in row.cells
        )
        labels = [item for item in row.cells if isinstance(item.value, str)
                  and len(item.value.strip()) >= 2
                  and re.sub(r"\s+", "", item.value).casefold() in folded]
        if not labels:
            continue
        matching_sheets.add(row.sheet_name)
        if row.sheet_name != cell.sheet_name:
            continue
        if data_row:
            row_numbers.add(row.row_number)
        elif row.row_number < int(re.search(r"\d+", cell.address).group()):
            columns.update(column_number(item.address) for item in labels)
    if matching_sheets and cell.sheet_name not in matching_sheets:
        return "요청한 원본 항목이 있는 시트와 변경 대상 시트가 다릅니다."
    row_number = int(re.search(r"\d+", cell.address).group())
    if row_numbers and row_number not in row_numbers:
        return "요청한 항목의 원본 행과 변경 대상 행이 다릅니다."
    if columns and column_number(cell.address) not in columns:
        return "요청한 항목의 원본 열과 변경 대상 열이 다릅니다."
    if columns and not row_numbers and not re.search(r"모두|전체|각각|모든|\ball\b|every", instruction, re.I):
        possible = {row.row_number for row in index.rows if row.sheet_name == cell.sheet_name
                    and any(column_number(item.address) in columns
                            and isinstance(item.value, (int, float)) for item in row.cells)}
        if len(possible) > 1:
            return "요청한 열에 여러 항목이 있어 변경할 행 또는 전체 적용 여부를 지정해야 합니다."
    return None
