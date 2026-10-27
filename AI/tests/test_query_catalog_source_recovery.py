"""Source catalogs retain requested blocks and wide publisher series tables."""
from dataclasses import replace

from openpyxl import Workbook

from app.agent.query.tabular_catalog import build_query_tables, query_catalog
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_validation import validated_table
from tests.tabular_query_fixtures import table_fixture
from tests.support.large_workbook_fixtures import offline, parsed


def _series(width=3):
    return table_fixture([
        (4, 3, [["Observation"] + [f"Measured quantity {i}" for i in range(1, width)],
                ["Series identifier codes"] + [f"AB{i}" for i in range(1, width)],
                ["Unit"] + ["kg"] * (width - 1)]),
        (7, 3, [["Release Date"] + ["03-05-2026"] * (width - 1)]),
        (8, 3, [["Next release"] + ["21 June 2026"] * (width - 1),
                ["Important Notes"] + [""] * (width - 1),
                ["2017"] + [i * 3 for i in range(1, width)],
                ["2018"] + [i * 4 for i in range(1, width)]])], sheet_name="Measurements")


def test_adjacent_descriptor_identifier_and_metadata_bands_form_one_table():
    summary, index = _series()
    tables = build_query_tables(summary)
    assert len(tables) == 1
    table = tables[0]
    assert table.reference == "C4:E11"
    assert table.metadata_rows == frozenset(range(5, 10))
    assert [row.row_number for row in table.rows] == [10, 11]
    assert table.columns[1].source_identifiers == (("Measurements!D5", "AB1"),)
    assert validated_table(table, index, {"D"})
    plan = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["D"],
                            filters=[TabularFilter(column_id="C", operator="equals", value="2017")])
    answer = execute_tabular_query(plan, summary, index, "2017년 AB1 Measured quantity 1 값은?")
    assert answer is not None and answer.status == "answered", answer
    assert "3" in answer.answer
    assert answer.verification.level == "request_checked"


def test_wide_catalog_keeps_requested_far_right_series_and_source_axis():
    summary, _ = _series(100)
    catalog = query_catalog(summary, "2018년 AB98 Measured quantity 98 값은?")
    assert len(catalog) == 1
    table = catalog[0]
    columns = table["columns"]
    assert columns[0]["column_id"] == "C"
    assert any(column["source_identifiers"] == [("Measurements!CW5", "AB98")] for column in columns)
    assert table["column_count"] == 100
    assert table["omitted_column_count"] > 0
    assert len(str(catalog)) < 30_000
    assert any(row["row_number"] == 11 for row in table["matching_source_rows"])


def test_unrecognized_record_label_is_not_dropped_as_metadata():
    summary, _ = table_fixture([(1, 1, [
        ["Period", "Output", "Input"], ["Series code", "AA1", "BB2"],
        ["Ordinary account", "missing", "pending"], ["2017", 10, 20], ["2018", 15, 25]])])
    table = build_query_tables(summary)[0]
    assert table.metadata_rows == frozenset({2})
    assert 3 in {row.row_number for row in table.rows}


def test_numeric_body_recovers_only_adjacent_plain_header_and_keeps_duplicate_table():
    summary, index = table_fixture([
        (2, 3, [["Instructions", None, None], ["Step", "Charge", "Optional note"]]),
        (4, 3, [[1, 17, None], [2, 23, None], [3, 19, None]]),
        (9, 3, [["Step", "Charge"], [1, 170], [2, 230], [3, 190]])], sheet_name="Schedule")
    tables = build_query_tables(summary)
    assert {table.id for table in tables} >= {"Schedule!C3:D6", "Schedule!C9:D12"}
    table = next(table for table in tables if table.reference == "C3:D6")
    assert validated_table(table, index, {"C", "D"})
    assert query_catalog(summary, "Schedule 시트 C3:D6에서 Charge 합계")[0]["table_id"] == table.id
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["D"], statistic="sum")
    answer = execute_tabular_query(plan, summary, index, "Schedule 시트 C3:D6에서 Charge 합계")
    assert answer is not None and "59" in answer.answer
    wrong = plan.model_copy(update={"table_id": "Schedule!C9:D12"})
    assert execute_tabular_query(wrong, summary, index, "Schedule 시트 C3:D6에서 Charge 합계") is None


def test_header_is_not_inferred_across_a_blank_or_from_a_numeric_record():
    for header in (["Step", "Charge"], [1, 23]):
        summary, _ = table_fixture([(1, 1, [header]), (3, 1, [[2, 45], [3, 56]])])
        assert not any(table.reference.startswith("A1:") for table in build_query_tables(summary))


def test_forged_series_code_cannot_certify_a_different_column():
    summary, index = _series()
    table = build_query_tables(summary)[0]
    columns = list(table.columns)
    columns[1] = replace(columns[1], source_identifiers=(("Measurements!D5", "WRONG7"),))
    assert not validated_table(replace(table, columns=tuple(columns)), index, {"D"})


def test_source_stream_revalidates_all_metadata_and_code_cells():
    book = Workbook()
    sheet = book.active
    sheet.title = "Independent series"
    for values in [["Period", "Long output label", "Long input label"],
                   ["Series code", "ZZ8", "YY9"], ["Unit", "kg", "kg"],
                   ["Release Date", "2026-05-02", "2026-05-02"],
                   ["Next release", "2026-06-02", "2026-06-02"],
                   ["Important Notes", None, None], ["2017", 23, 17], ["2018", 37, 41]]:
        sheet.append(values)
    summary, index, _ = parsed(book)
    table = build_query_tables(summary)[0]
    assert table.metadata_rows == frozenset(range(2, 7))
    index = replace(index, rows=tuple(row for row in index.rows if row.row_number <= 3),
                    truncated=True, truncated_sheet_names=frozenset({sheet.title}))
    plan = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["B"],
                            filters=[TabularFilter(column_id="A", operator="equals", value="2018")])
    answer = execute_tabular_query(plan, summary, index, "2018년 ZZ8 Long output label 값은?")
    assert answer is not None and "37" in answer.answer
    assert answer.verification.level == "request_checked"
    assert "full_source_scan" in answer.verification.checks
