from io import BytesIO
from zipfile import ZipFile

from app.agent.writeback.macro_verification import (
    UNREADABLE, add_macro_check, vba_digest,
)


def package(parts: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    return buffer.getvalue()


MACRO = package({"xl/vbaProject.bin": b"macro-bytes"})
OTHER_MACRO = package({"xl/vbaProject.bin": b"other-bytes"})
NO_MACRO = package({"xl/workbook.xml": b"<workbook/>"})
BROKEN = b"not a zip package at all"


def check(before: bytes, after: bytes, keep_vba: bool = True):
    checks: list = []
    add_macro_check(checks, before, after, keep_vba)
    return checks[0]


def test_unchanged_macro_project_passes() -> None:
    assert check(MACRO, MACRO).passed


def test_replaced_macro_project_fails() -> None:
    assert not check(MACRO, OTHER_MACRO).passed


def test_dropped_macro_project_fails() -> None:
    assert not check(MACRO, NO_MACRO).passed


def test_unreadable_package_fails_instead_of_passing_quietly() -> None:
    assert vba_digest(BROKEN) is UNREADABLE
    assert not check(BROKEN, BROKEN).passed
    assert not check(MACRO, BROKEN).passed
    assert not check(BROKEN, MACRO).passed


def test_workbook_without_macros_is_reported_as_such() -> None:
    result = check(NO_MACRO, NO_MACRO, keep_vba=False)
    assert result.passed and "매크로가 없는" in result.detail
