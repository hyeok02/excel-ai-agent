"""Macro preservation, checked so that 'cannot look' never reads as 'unchanged'.

The write-back gate compares the uploaded workbook with the edited copy. A
package that fails to open yields no digest, and comparing two absent digests
would quietly pass the macro check. This module keeps the two cases apart.
"""
import hashlib
from io import BytesIO
from zipfile import ZipFile

from app.agent.writeback.models import VerificationCheck

UNREADABLE = object()


def vba_digest(content: bytes):
    """The VBA digest, or None when the package simply holds no macro part.

    Returns UNREADABLE when the package cannot be opened, so callers can tell
    an absent macro project from a check that could not be carried out.
    """
    try:
        with ZipFile(BytesIO(content)) as archive:
            name = next(
                (item for item in archive.namelist()
                 if item.endswith("vbaProject.bin")),
                None,
            )
            return hashlib.sha256(archive.read(name)).hexdigest() if name else None
    except Exception:
        return UNREADABLE


def add_macro_check(checks, before: bytes, after: bytes, keep_vba: bool) -> None:
    if not keep_vba:
        checks.append(_check("macros", True, "매크로가 없는 .xlsx 파일"))
        return
    original, modified = vba_digest(before), vba_digest(after)
    if UNREADABLE in (original, modified):
        checks.append(_check("macros", False, "VBA 프로젝트를 확인할 수 없어 중단"))
        return
    checks.append(_check("macros", original == modified, "VBA 프로젝트 보존"))


def _check(name: str, passed: bool, detail: str) -> VerificationCheck:
    return VerificationCheck(name=name, passed=passed, detail=detail)
