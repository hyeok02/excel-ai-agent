from app.services.insights.display.glossary import readable
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report

HOLDER = "International Business Machines Corporation"


def _series(metric, old, new, row):
    return {
        "metric": metric, "scope": None, "label_cell": f"B{row}",
        "scope_cell": None, "basis": None,
        "points": [
            {"period": "2021-12-31T00:00:00", "value": old,
             "period_cell": "C1", "value_cell": f"C{row}"},
            {"period": "2025-12-31T00:00:00", "value": new,
             "period_cell": "D1", "value_cell": f"D{row}"},
        ],
    }


def _context():
    identity = {"holder": HOLDER, "evidence": ["'Key Stats'!A1"]}
    return {"identity": identity, "sheets": [{"name": "Key Stats", "business_facts": {
        "identity": identity,
        "horizontal_series": [
            _series("Total Revenue", 57351, 67535, 5),
            _series("Net Income", 5743, 10593, 6),
            _series("- Cash & Short Term Investments", 100, 200, 7),
        ],
    }}]}


def test_the_workbook_subject_is_not_repeated_on_every_card() -> None:
    items, overview = horizontal_trend_report(_context())

    assert items
    assert not any(HOLDER in item.title for item in items)
    assert not any(HOLDER in item.fact for item in items)
    assert HOLDER not in overview


def test_metric_titles_keep_their_own_name() -> None:
    titles = [item.title for item in horizontal_trend_report(_context())[0]]

    assert "총매출(Total Revenue) 변화" in titles
    assert "순이익(Net Income) 변화" in titles


def test_indent_marks_are_dropped_from_source_labels() -> None:
    assert readable("- Cash & Short Term Investments") == "Cash & Short Term Investments"
    assert readable("• Short Term Investments") == "Short Term Investments"
    assert readable("Total Revenue") == "총매출(Total Revenue)"
