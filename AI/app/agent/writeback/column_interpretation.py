"""Read a Korean column word as the one foreign-language source header it names.

"Carrot 단가를 2로" names the column in Korean while the sheet says "UnitPrice".
Target authorization only accepts words that are source labels, so it blocks this
request. The model's draft already chose a column; when every drafted cell is in
that one column, its header is written in another script (Latin) and exactly one
Korean word of the target part names no source label, that word is read as the
header. The reading is stated to the user before approval. An unknown word in the
header's own script ("UnknownMetric") is a missing name, never an alias.
"""
import re

from app.agent.tools.workbook_header_index import detect_header_rows
from app.agent.writeback.natural_operations import ASSIGNMENT
from app.agent.writeback.references import column_number, expand_reference
from app.agent.writeback.target_semantics import _label_matches, unknown_subject_tokens
from app.agent.writeback.target_syntax import sheet_mentions

HANGUL = re.compile(r"[가-힣]")


def interpreted_instruction(instruction, drafts, index):
    """(instruction to authorize, note for the user or None)."""
    column = _single_column(drafts)
    if column is None or len(ASSIGNMENT.split(instruction, maxsplit=1)) < 2:
        return instruction, None
    sheet, number, first_row = column
    header = _header(index, sheet, number, first_row)
    if header is None or HANGUL.search(header) or _label_matches(header, instruction):
        return instruction, None
    prefix = ASSIGNMENT.split(instruction, maxsplit=1)[0]
    sheets = {row.sheet_name for row in index.rows}
    named = {name for _, _, name in sheet_mentions(prefix, sheets)}
    labels = {str(cell.value) for row in index.rows if row.sheet_name == sheet for cell in row.cells
              if _label_matches(cell.value, prefix)}
    unknown = unknown_subject_tokens(prefix, labels, named)
    if len(unknown) != 1 or not HANGUL.search(unknown[0]):
        return instruction, None
    word = unknown[0]
    rewritten = prefix.replace(word, f" {header} ", 1) + instruction[len(prefix):]
    return rewritten, f"요청의 ‘{word}’를 원본 ‘{header}’ 열로 해석했습니다. 승인 전에 대상 열을 확인해 주세요."


def _single_column(drafts):
    cells = {(draft.sheet_name, reference) for draft in drafts for reference in expand_reference(draft.reference)}
    columns = {(sheet, column_number(reference)) for sheet, reference in cells}
    if len(columns) != 1:
        return None
    sheet, number = columns.pop()
    return sheet, number, min(int(re.search(r"\d+", reference).group()) for _, reference in cells)


def _header(index, sheet, number, first_row):
    header_rows = detect_header_rows(index.rows).header_rows.get(sheet, set())
    above = [row for row in header_rows if row < first_row]
    if not above:
        return None
    row = next((item for item in index.rows if item.sheet_name == sheet and item.row_number == max(above)), None)
    cell = next((item for item in row.cells if column_number(item.address) == number), None) if row else None
    return cell.value.strip() if cell is not None and isinstance(cell.value, str) and cell.value.strip() else None
