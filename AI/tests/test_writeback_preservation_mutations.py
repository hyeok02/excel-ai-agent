from io import BytesIO
from zipfile import ZipFile

import pytest

from app.agent.writeback import editor
from app.agent.writeback.models import WritebackChange
from tests.test_writeback_apply_safety import workbook


@pytest.mark.parametrize("path,before,after", [
    ("xl/worksheets/sheet1.xml", b'<v>1</v>', b'<v>999</v>'),
    ("xl/worksheets/sheet1.xml", b'defaultRowHeight="15"', b'defaultRowHeight="22"'),
    ("xl/workbook.xml", b'activeTab="0"', b'activeTab="1"'),
])
def test_verification_rejects_corruption_outside_the_approved_cell(monkeypatch, path, before, after):
    original_patch = editor.patch_workbook_package

    def corrupt(content, changes):
        patched = original_patch(content, changes)
        output = BytesIO()
        with ZipFile(BytesIO(patched)) as source, ZipFile(output, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == path:
                    assert before in data
                    data = data.replace(before, after, 1)
                target.writestr(info, data)
        return output.getvalue()

    monkeypatch.setattr(editor, "patch_workbook_package", corrupt)
    changes = [WritebackChange(sheet_name="Data", reference="B1", old_value=10,
                              new_value=11, reason="approved", value_type="number")]
    with pytest.raises(editor.UnsafeWritebackError, match="보존 검증"):
        editor.apply_writeback("generic.xlsx", workbook(), changes)


def test_valid_application_proves_same_sheet_non_targets_unchanged():
    change = WritebackChange(sheet_name="Data", reference="B1", old_value=10,
                             new_value=11, reason="approved", value_type="number")
    _, manifest = editor.apply_writeback("generic.xlsx", workbook(), [change])
    assert manifest.verified
    check = next(item for item in manifest.checks if item.name == "unapproved_content")
    assert check.passed
