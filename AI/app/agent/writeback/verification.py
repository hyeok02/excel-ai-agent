import hashlib
from io import BytesIO
from zipfile import ZipFile

from app.services.workbook_loading import close_workbook, load_workbook_for_reading

from app.agent.writeback.models import VerificationCheck

def workbook_fingerprint(content: bytes, keep_vba: bool) -> dict[str, object]:
    workbook = load_workbook_for_reading(content, keep_vba=keep_vba)
    try:
        return {
            "sheets": tuple(workbook.sheetnames),
            "formulas": _formulas(workbook),
            "merged": _merged(workbook),
            "styles": _styles(workbook),
        }
    finally:
        close_workbook(workbook)

def compare_fingerprints(before, after, changes) -> list[VerificationCheck]:
    targets = {(change.sheet_name, change.reference) for change in changes}
    unchanged_formula_targets = {
        target for target in targets if not _is_formula_change(changes, target)
    }
    formulas_preserved = all(
        before["formulas"].get(target) == after["formulas"].get(target)
        for target in unchanged_formula_targets
    ) and all(
        before["formulas"].get(target) == after["formulas"].get(target)
        for target in set(before["formulas"]) | set(after["formulas"])
        if target not in targets
    )
    formulas_applied = all(
        after["formulas"].get((change.sheet_name, change.reference)) == change.new_value
        for change in changes
        if _is_formula_value(change.new_value)
    )
    unchanged_styles = all(
        before["styles"].get(target, 0) == after["styles"].get(target, 0)
        for target in targets
    )
    return [
        _check("sheet_structure", before["sheets"] == after["sheets"], "시트 구성 보존"),
        _check(
            "formulas",
            formulas_preserved and formulas_applied,
            "승인 대상 외 수식 보존 및 승인 수식 반영",
        ),
        _check("merged_cells", before["merged"] == after["merged"], "병합 영역 보존"),
        _check("styles", unchanged_styles, "변경 셀 서식 보존"),
    ]

def package_checks(
    before: bytes, after: bytes, changed_paths: set[str]
) -> list[VerificationCheck]:
    with ZipFile(BytesIO(before)) as original, ZipFile(BytesIO(after)) as modified:
        original_names, modified_names = set(original.namelist()), set(modified.namelist())
        unchanged = original_names - changed_paths
        parts_preserved = all(
            original.read(name) == modified.read(name) for name in unchanged
        )
        features_preserved = all(
            _features(original.read(path)) == _features(modified.read(path))
            for path in changed_paths
        )
    return [
        _check("package_structure", original_names == modified_names, "파일 구성 요소 보존"),
        _check("unchanged_parts", parts_preserved, "변경 시트 외 원본 부품 보존"),
        _check("excel_extensions", features_preserved, "유효성·확장 기능 보존"),
        _check("recalculation", _recalculation_requested(after), "Excel 실행 시 수식 재계산"),
    ]

def vba_digest(content: bytes) -> str | None:
    try:
        with ZipFile(BytesIO(content)) as archive:
            name = next((item for item in archive.namelist() if item.endswith("vbaProject.bin")), None)
            return hashlib.sha256(archive.read(name)).hexdigest() if name else None
    except Exception:
        return None

def add_macro_check(checks, before: bytes, after: bytes, keep_vba: bool) -> None:
    if not keep_vba:
        checks.append(_check("macros", True, "매크로가 없는 .xlsx 파일"))
        return
    original, modified = vba_digest(before), vba_digest(after)
    checks.append(_check("macros", original == modified, "VBA 프로젝트 보존"))

def _formulas(workbook) -> dict[tuple[str, str], str]:
    return {
        (sheet.title, cell.coordinate): cell.value
        for sheet in workbook.worksheets
        for row in sheet.iter_rows()
        for cell in row
        if isinstance(cell.value, str) and cell.value.startswith("=")
    }

def _merged(workbook) -> dict[str, tuple[str, ...]]:
    return {
        sheet.title: tuple(sorted(str(item) for item in sheet.merged_cells.ranges))
        for sheet in workbook.worksheets
    }

def _styles(workbook) -> dict[tuple[str, str], int]:
    return {
        (sheet.title, cell.coordinate): cell.style_id
        for sheet in workbook.worksheets
        for row in sheet.iter_rows()
        for cell in row
        if cell.value is not None or cell.has_style
    }


def _check(name: str, passed: bool, detail: str) -> VerificationCheck:
    return VerificationCheck(name=name, passed=passed, detail=detail)


def _is_formula_value(value: object) -> bool:
    return isinstance(value, str) and value.lstrip().startswith("=")


def _is_formula_change(changes, target: tuple[str, str]) -> bool:
    return any(
        (change.sheet_name, change.reference) == target
        and _is_formula_value(change.new_value)
        for change in changes
    )


def _features(content: bytes) -> tuple[bytes, ...]:
    return tuple(
        match.group(0)
        for tag in (b"dataValidations", b"conditionalFormatting", b"extLst")
        for match in __import__("re").finditer(
            rb"<" + tag + rb"\b.*?</" + tag + rb">", content, __import__("re").DOTALL
        )
    )


def _recalculation_requested(content: bytes) -> bool:
    with ZipFile(BytesIO(content)) as archive:
        workbook = archive.read("xl/workbook.xml")
    return all(
        attribute in workbook
        for attribute in (
            b'calcMode="auto"',
            b'fullCalcOnLoad="1"',
            b'forceFullCalc="1"',
        )
    )
