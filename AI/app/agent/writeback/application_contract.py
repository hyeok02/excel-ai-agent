"""Validate the approved application payload before touching workbook XML."""
from math import isfinite

from openpyxl.utils.cell import range_boundaries

from app.agent.writeback.references import CELL_REFERENCE


def validate_application_contract(change):
    reference = change.reference.upper()
    if not CELL_REFERENCE.fullmatch(reference):
        raise ValueError("적용 대상은 범위가 아닌 단일 셀 주소여야 합니다.")
    column, row, _, _ = range_boundaries(reference)
    if column > 16_384 or row > 1_048_576:
        raise ValueError("Excel의 최대 행·열 범위를 벗어난 셀 주소입니다.")
    for value in (change.old_value, change.new_value):
        if isinstance(value, float) and not isfinite(value):
            raise ValueError("Excel에는 유한한 숫자만 저장할 수 있습니다.")
    formula = isinstance(change.new_value, str) and change.new_value.lstrip().startswith("=")
    if formula != (change.value_type == "formula") or formula != (change.change_type == "formula"):
        raise ValueError("승인한 변경 종류와 새 수식 값의 형식이 일치하지 않습니다.")
