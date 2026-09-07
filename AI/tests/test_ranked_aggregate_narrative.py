"""Regression coverage for ranked tables with a category aggregate."""

import pytest

from app.services.insights.quality import build_source_report
from app.services.insights.reference_matching import matching_references
from app.services.insights.validation_index import extract_references
from app.services.insights.validator import validate_workbook_insights


VARIANTS = [
    (("순위", "이름", "유형", "수량", "비중 (%)"), "기관",
     ("가온 조합", "나래 기금", "다온 신탁", "라온 개인")),
    (("Rank", "Name", "Category", "Quantity", "Share (%)"), "Institutional",
     ("Group North", "Fund East", "Trust West", "Person South")),
]


def _cell(address, value, label=None):
    result = {"cell": address, "value": value}
    if label:
        result["label"] = label
    return result


def _context(headers, institution, names):
    types = [institution, institution, institution,
             "개인" if institution == "기관" else "Individual"]
    # Physical order is intentionally not rank order.
    rows = [
        (2, names[1], types[0], 1800, 18),
        (1, names[0], types[1], 4200, 42),
        (3, names[2], types[2], 900, 9),
        (4, names[3], types[3], 3100, 31),
    ]
    table_rows = [[_cell(f"{column}1", value)
                   for column, value in zip("ABCDE", headers)]]
    selected = []
    for row_number, values in enumerate(rows, start=2):
        cells = [_cell(f"{column}{row_number}", value, label)
                 for column, value, label in zip("ABCDE", values, headers)]
        table_rows.append(cells)
        selected.append({"location": f"현황!A{row_number}:E{row_number}",
                         "values": cells})
    return {"omitted_sheet_count": 0, "sheets": [{
        "name": "현황", "business_facts": {
            "selected_records": selected, "table_rows": table_rows,
            "numeric_changes": [], "time_series": [],
        },
    }]}


def _result(variant):
    context = _context(*variant)
    report = build_source_report(context)
    return validate_workbook_insights(report, context)


def _covers(insight, address):
    cited = set().union(*(extract_references(item) for item in insight.evidence))
    expected = f"현황!{address}".casefold()
    return any(matching_references(reference, {expected}) for reference in cited)


def _plain(text):
    return text.replace(",", "")


@pytest.mark.parametrize("variant", VARIANTS)
def test_selects_category_share_and_top_rank_as_core_facts(variant):
    headers, institution, names = variant
    result = _result(variant)
    aggregate = [item for item in result.insights
                 if institution.casefold() in item.fact.casefold()
                 and "69" in _plain(item.fact)]
    top = [item for item in result.insights
           if names[0].casefold() in item.fact.casefold()]

    assert aggregate, "The three institutional shares should be summarized as 69%."
    assert top, "The row explicitly ranked first should be selected as a core fact."
    assert "%" in aggregate[0].fact
    assert "1" in top[0].fact
    assert "42" in _plain(top[0].fact)
    assert "4200" in _plain(top[0].fact)
    assert institution.casefold() in result.overview.casefold()
    assert names[0].casefold() in result.overview.casefold()


@pytest.mark.parametrize("variant", VARIANTS)
def test_aggregate_cites_only_rows_that_contribute_to_the_category_total(variant):
    institution = variant[1]
    aggregate = next(item for item in _result(variant).insights
                     if institution.casefold() in item.fact.casefold()
                     and "69" in _plain(item.fact))

    for row in (2, 3, 4):
        assert _covers(aggregate, f"C{row}")
        assert _covers(aggregate, f"E{row}")
    assert not _covers(aggregate, "C5")
    assert not _covers(aggregate, "E5")
    assert "23" not in _plain(aggregate.fact), "Do not average the three shares."


@pytest.mark.parametrize("variant", VARIANTS)
def test_top_rank_fact_cites_rank_name_quantity_and_share_from_one_row(variant):
    expected_name = variant[2][0]
    top = next(item for item in _result(variant).insights
               if expected_name.casefold() in item.fact.casefold())

    for address in ("A3", "B3", "D3", "E3"):
        assert _covers(top, address)
    assert not _covers(top, "B2")
    assert "Riot Games" not in top.model_dump_json()


def test_category_shares_from_different_periods_are_not_added_together():
    rows = [[
        _cell("A1", "Rank"), _cell("B1", "Name"), _cell("C1", "Category"),
        _cell("D1", "Period"), _cell("E1", "Share (%)"),
    ], [
        _cell("A2", 1), _cell("B2", "Fund A"), _cell("C2", "Institutional"),
        _cell("D2", "2024"), _cell("E2", 20),
    ], [
        _cell("A3", 2), _cell("B3", "Fund B"), _cell("C3", "Institutional"),
        _cell("D3", "2025"), _cell("E3", 30),
    ]]
    context = {"sheets": [{"name": "Ownership", "business_facts": {
        "table_regions": [{"rows": rows}],
    }}]}

    report = build_source_report(context)

    assert all("비중 합계는 50%" not in item.fact for item in report.insights)
