"""Describe unsupported embedded models without mistaking cover text for data."""
from collections import Counter
from io import BytesIO
from zipfile import ZipFile

from defusedxml.ElementTree import fromstring

from app.services.sheet_classification.models import SheetRole

DATA_MODEL_LIMITATION = (
    "Power Pivot 내부 데이터 모델이 포함되어 있습니다. 내부 모델은 직접 읽거나 새로고침하지 않으며, "
    "선택한 워크시트에 저장된 셀 데이터만 분석합니다."
)
DATA_MODEL_ONLY_MESSAGE = (
    "Power Pivot 내부 데이터 모델이 있지만 선택한 워크시트에서는 분석할 셀 표를 확인하지 못했습니다. "
    "안내 문구를 업무 데이터로 대신 분석하지 않았습니다. "
    "Excel에서 내부 모델의 데이터를 워크시트 표로 내보낸 뒤 .xlsx로 저장해 주세요. "
    "숨김 시트에 셀 표가 있다면 숨김 시트 포함 옵션으로 다시 시도할 수 있습니다."
)
LEGACY_XLS_MESSAGE = (
    "구형 .xls 파일은 직접 분석하지 않습니다. "
    "Excel에서 '다른 이름으로 저장'으로 .xlsx 형식으로 변환해 주세요. "
    "파일 이름의 확장자만 바꾸면 변환되지 않습니다."
)


def has_embedded_data_model(content: bytes) -> bool:
    """Use OOXML feature metadata, not workbook/sheet names or source vendors."""
    with ZipFile(BytesIO(content)) as archive:
        content_types = fromstring(archive.read("[Content_Types].xml"), forbid_dtd=True)
        parts = {name.casefold() for name in archive.namelist()}
    return any(
        (entry.get("ContentType") or "").casefold().endswith(".model+data")
        and (
            (entry.get("PartName") or "").lstrip("/").casefold() in parts
            or bool(entry.get("Extension")) and any(
                name.endswith("." + entry.get("Extension").casefold()) for name in parts
            )
        )
        for entry in content_types
    )


def has_worksheet_data(worksheet, classification) -> bool:
    """Only identify a conservative narrative-only/empty boundary.

    A workbook containing a model can still contain ordinary values, cached
    formulas, text records, or exported tables. Those must remain usable. The
    classification alone is insufficient: short one-column labels and multi-
    column text tables remain data even if a heuristic calls them documentation.
    """
    cells = [cell for cell in worksheet._cells.values() if cell.value is not None]
    if not cells:
        return False
    if worksheet.tables or any(cell.data_type == "f" or not isinstance(cell.value, str) for cell in cells):
        return True
    if any(count > 1 for count in Counter(cell.row for cell in cells).values()):
        return True
    if classification.role is not SheetRole.DOCUMENTATION:
        return True
    ordered = sorted(cells, key=lambda cell: (cell.row, cell.column))
    # A one-column free-text table is still data when it has a compact header
    # followed by contiguous records, even if those records are long sentences.
    if len(ordered) >= 3 and len(ordered[0].value.strip()) < 80 and all(
        cell.column == ordered[0].column and cell.row == ordered[0].row + offset
        for offset, cell in enumerate(ordered[:3])
    ):
        return True
    # A compact, one-column code/category list is not a cover/instructions page.
    return not any(len(cell.value.strip()) >= 80 for cell in cells)
