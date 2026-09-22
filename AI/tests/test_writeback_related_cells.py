"""수식으로 이어져 있지 않아 함께 고쳐야 하는 셀을 찾는 규칙 검증."""
from app.agent.writeback.related_cells import dedupe_related, related_cells

HEADERS = {"G": "일반관리", "N": "연구개발", "R": "영업", "W": "서비스", "F": "총계"}
ROWS = {
    108: {"G": 1200, "N": 1300, "R": 1836, "W": 1081},
    109: {"G": 1210, "N": 1290, "R": 1800, "W": 1050},
    110: {"G": 1150, "N": 1320, "R": 1790, "W": 1020},
    111: {"G": 1180, "N": 1260, "R": 1880, "W": 1100},
    112: {"G": 1220, "N": 1350, "R": 1910, "W": 1075},
    113: {"G": 1240, "N": 1310, "R": 1860, "W": 1090},
}
SERVICES = [ROWS[number]["W"] for number in sorted(ROWS)]


def budget_sheet() -> dict:
    columns = {letter: {107: header} for letter, header in HEADERS.items()}
    for number, values in ROWS.items():
        for letter, value in values.items():
            columns[letter][number] = value
        columns["F"][number] = sum(values.values())
    return columns


def chart_sheet(values: list | None = None) -> dict:
    series = SERVICES if values is None else values
    column = {6: "서비스"}
    column.update({7 + step: value for step, value in enumerate(series)})
    return {"BS": column}


def sheets(chart: dict | None = None) -> dict:
    return {"부서현황": budget_sheet(), "Chart_Data": chart or chart_sheet()}


def find(reference: str = "W108", new_value: object = 1000, **kwargs) -> list:
    return related_cells(sheets(**kwargs), "부서현황", reference, new_value)


def test_finds_hardcoded_row_total_and_adjusts_it():
    found = [cell for cell in find() if cell.kind == "total"]

    assert len(found) == 1
    assert (found[0].sheet_name, found[0].reference) == ("부서현황", "F108")
    assert found[0].current_value == 5417
    assert found[0].suggested_value == 5417 - 1081 + 1000


def test_finds_the_same_series_duplicated_on_another_sheet():
    found = [cell for cell in find() if cell.kind == "mirror"]

    assert len(found) == 1
    assert (found[0].sheet_name, found[0].reference) == ("Chart_Data", "BS7")
    assert found[0].current_value == 1081
    assert found[0].suggested_value == 1000


def test_every_related_cell_explains_why_it_has_to_change_together():
    for cell in find():
        assert "수식" in cell.reason
        assert cell.reference in cell.reason or cell.sheet_name in cell.reason


def test_ignores_a_sheet_that_holds_a_different_series():
    changed = [value + 1 for value in SERVICES]

    assert [cell for cell in find(chart=chart_sheet(changed)) if cell.kind == "mirror"] == []


def test_ignores_a_series_the_other_sheet_only_partly_repeats():
    assert [cell for cell in find(chart=chart_sheet(SERVICES[:3])) if cell.kind == "mirror"] == []


def test_skips_a_cell_whose_value_is_zero_because_any_sum_would_fit():
    columns = budget_sheet()
    columns["W"][108] = 0
    columns["F"][108] = sum(columns[letter][108] for letter in ("G", "N", "R", "W"))

    assert related_cells({"부서현황": columns}, "부서현황", "W108", 30) == []


def test_skips_non_numeric_and_unknown_targets():
    assert find(new_value="서비스팀") == []
    assert find(reference="ZZ9999") == []
    assert related_cells(sheets(), "없는시트", "W108", 1000) == []


def test_reports_at_most_four_cells():
    assert len(find()) <= 4


class FakeChange:
    def __init__(self, sheet_name, reference, related):
        self.sheet_name = sheet_name
        self.reference = reference
        self.related_cells = related


def test_drops_a_related_cell_that_is_already_a_change_of_its_own():
    total, mirror = find()
    changes = [
        FakeChange("부서현황", "W108", [total, mirror]),
        FakeChange("Chart_Data", "bs7", []),
    ]

    dedupe_related(changes)

    assert [cell.reference for cell in changes[0].related_cells] == ["F108"]
