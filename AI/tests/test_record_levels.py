"""Record lists that are not added up: years as columns, averages said above the table, rows of several
levels."""
import app.main  # noqa: F401  (the application's import order)
from app.services.insights.narratives.record_levels import not_summable


def _cells(row, values):
    return [{"cell": f"{letter}{row}", "value": value} for letter, value in zip("ABCD", values)]


def _sheet(rows):
    return {"business_facts": {"table_regions": [{"rows": rows}]}}


def test_years_as_columns_and_an_average_said_above_are_not_added_up():
    records = [dict(enumerate(_cells(row, ["A", 1, 2]), 1)) for row in (3, 4)]
    assert not_summable(_sheet([]), _cells(2, ["Inventory", "1990", "1991"]), records)
    title = _cells(1, ["Timeseries of the average number of beds"])
    header = _cells(2, ["Month", "Beds"])
    month = [dict(enumerate(_cells(row, [f"2024-0{row}", 10.5 + row]), 1)) for row in (3, 4, 5)]
    assert not_summable(_sheet([title, header]), header, month)
    assert not not_summable(_sheet([header]), header, month)


def test_rows_of_several_levels_are_not_added_up():
    header = _cells(1, ["Name", "Level", "People"])
    def rows(items):
        return [dict(enumerate(_cells(row, item), 1)) for row, item in enumerate(items, 2)]
    nested = rows([["England", "Country", 60], *[[f"R{n}", "Region", n] for n in (10, 12, 13, 11, 14)],
                   ["Leeds", "District", 3]])
    assert not_summable({}, header, nested)  # the five regions add up to England
    totalled = rows([["All", "Area", 30], ["A", "Area", 10], ["B", "Area", 20], ["C", "Town", 1]])
    assert not_summable({}, header, [*totalled[:3]])  # 'All' is the other rows' total
    flat = rows([["A", "X", 10], ["B", "X", 11], ["C", "Y", 12], ["D", "Y", 40]])
    assert not not_summable({}, header, flat)
