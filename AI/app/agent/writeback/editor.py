from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell

from app.agent.writeback.models import VerificationCheck, WritebackChange, WritebackManifest
from app.agent.writeback.package_editor import changed_worksheet_paths, patch_workbook_package
from app.agent.writeback.verification import (
    add_macro_check,
    compare_fingerprints,
    package_checks,
    workbook_fingerprint,
)


class UnsafeWritebackError(ValueError):
    """Raised when a requested workbook change cannot be applied safely."""


def apply_writeback(
    filename: str, content: bytes, changes: list[WritebackChange]
) -> tuple[bytes, WritebackManifest]:
    if not changes or len(changes) > 10:
        raise UnsafeWritebackError("한 번에 1~10개의 검증된 변경만 적용할 수 있습니다.")
    keep_vba = Path(filename).suffix.lower() == ".xlsm"
    before = workbook_fingerprint(content, keep_vba)
    workbook = load_workbook(BytesIO(content), data_only=False, keep_vba=keep_vba)
    try:
        _validate_changes(workbook, changes)
    finally:
        workbook.close()
    changed_paths = changed_worksheet_paths(content, changes)
    try:
        modified = patch_workbook_package(content, changes)
    except ValueError as exception:
        raise UnsafeWritebackError(str(exception)) from exception
    after = workbook_fingerprint(modified, keep_vba)
    checks = compare_fingerprints(before, after, changes)
    checks.extend(package_checks(content, modified, changed_paths))
    add_macro_check(checks, content, modified, keep_vba)
    checks.append(_verify_values(modified, changes, keep_vba))
    manifest = WritebackManifest(
        changed_cells=[f"{item.sheet_name}!{item.reference}" for item in changes],
        checks=checks,
        verified=all(check.passed for check in checks),
    )
    if not manifest.verified:
        raise UnsafeWritebackError("변경 후 보존 검증에 실패해 수정본을 생성하지 않았습니다.")
    return modified, manifest


def _validate_changes(workbook, changes: list[WritebackChange]) -> None:
    seen = set()
    for change in changes:
        key = (change.sheet_name, change.reference.upper())
        if key in seen or change.sheet_name not in workbook.sheetnames:
            raise UnsafeWritebackError("중복되거나 존재하지 않는 변경 대상입니다.")
        seen.add(key)
        cell = workbook[change.sheet_name][change.reference]
        if isinstance(cell, MergedCell):
            raise UnsafeWritebackError("병합 영역의 시작 셀만 수정할 수 있습니다.")
        if isinstance(cell.value, str) and cell.value.startswith("="):
            raise UnsafeWritebackError("수식 셀은 수정할 수 없습니다.")
        if cell.value != change.old_value:
            raise UnsafeWritebackError("승인한 기존 값과 현재 원본 값이 다릅니다.")
        if isinstance(change.new_value, str) and change.new_value.lstrip().startswith("="):
            raise UnsafeWritebackError("새 수식 입력은 허용하지 않습니다.")
        if isinstance(change.new_value, str) and len(change.new_value) > 32_767:
            raise UnsafeWritebackError("Excel 셀의 최대 문자열 길이를 초과했습니다.")


def _verify_values(content, changes, keep_vba) -> VerificationCheck:
    workbook = load_workbook(BytesIO(content), data_only=False, keep_vba=keep_vba)
    try:
        passed = all(
            workbook[item.sheet_name][item.reference].value == item.new_value
            for item in changes
        )
    finally:
        workbook.close()
    return VerificationCheck(name="changed_values", passed=passed, detail="승인한 값 반영")
