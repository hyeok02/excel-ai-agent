import json
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from tests.support.workbook_api_fixtures import upload


def workbook():
    book = Workbook()
    book.active.title = "Data"
    book.active.append([1, 10, "=A1+B1", True])
    book.active.merge_cells("A3:B3")
    book.active["A3"] = "Title"
    output = BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()


def apply(changes):
    return TestClient(app).post("/api/v1/workbooks/writebacks/apply",
                               data={"changes": json.dumps(changes)},
                               files=upload("generic.xlsx", workbook()))


def change(reference="B1", old=10, new=11, **kwargs):
    return {"sheet_name": "Data", "reference": reference, "old_value": old,
            "new_value": new, "reason": "approved", **kwargs}


@pytest.mark.parametrize("reference", ["A1:B1", "A0", "XFE1", "A1048577", "unknown"])
def test_invalid_apply_addresses_are_controlled_client_errors(reference):
    response = apply([change(reference)])
    assert response.status_code == 422


@pytest.mark.parametrize("reference,old,new", [("A1", True, 8), ("D1", 1, False)])
def test_boolean_and_numeric_original_values_are_not_interchangeable(reference, old, new):
    assert apply([change(reference, old, new)]).status_code == 422


@pytest.mark.parametrize("new,metadata", [
    ("=A1*2", {}), ("=A1*2", {"value_type": "text", "change_type": "formula"}),
    (12, {"value_type": "formula", "change_type": "formula"}),
    (None, {"value_type": "number", "change_type": "formula"}),
])
def test_formula_metadata_cannot_claim_a_text_cell_is_an_applied_formula(new, metadata):
    assert apply([change(new=new, **metadata)]).status_code == 422


@pytest.mark.parametrize("new", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_values_never_reach_excel_xml(new):
    assert apply([change(new=new)]).status_code == 422


def test_one_stale_change_fails_the_whole_batch_without_an_archive():
    response = apply([change(), change("A1", old=999, new=2)])
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")


def test_merged_non_anchor_fails_without_partial_application():
    assert apply([change(), change("B3", old=None, new=2)]).status_code == 422


def test_valid_typed_formula_is_applied_and_verified():
    response = apply([change(new="=A1*2", value_type="formula", change_type="formula")])
    assert response.status_code == 200
    with ZipFile(BytesIO(response.content)) as package:
        assert json.loads(package.read("manifest.json"))["verified"] is True
