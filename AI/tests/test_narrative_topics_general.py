"""Unrelated source shapes should supply their own topic, not a fixed heading."""
import pytest

from app.services.insights.models import WorkbookInsightReport
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report
from app.services.insights.narratives.ranked_narratives import ranked_report
from app.services.insights.narratives.table_narratives import table_report
from app.services.insights.narratives.topic_labels import source_topic
from app.services.insights.verification.validator import validate_workbook_insights


def cell(address, value):
    return {"cell": address, "value": value, "number_format": "General"}


def validated_topic(source, reporter):
    items, overview = reporter(source)
    assert items
    report = validate_workbook_insights(
        WorkbookInsightReport(overview=overview, insights=items), source,
    )
    assert report.insights
    return report.insights[0].topic


def test_date_table_topic_comes_from_its_cited_measurement_label():
    rows = [
        [cell("A1", "항목"), cell("B1", "2025-01-01"), cell("C1", "2025-02-01")],
        [cell("A2", "열량"), cell("B2", 700), cell("C2", 740)],
    ]
    source = {"sheets": [{"name": "식단", "business_facts": {
        "table_regions": [{"rows": rows}],
    }}]}

    assert validated_topic(source, table_report) == "열량"


def test_ranked_table_topic_comes_from_its_cited_entry_name():
    rows = [
        [cell("A1", "Rank"), cell("B1", "Name"), cell("C1", "Shares Held"),
         cell("D1", "Share (%)")],
        [cell("A2", 1), cell("B2", "Primary Fund"), cell("C2", 1000),
         cell("D2", 42)],
    ]
    source = {"sheets": [{"name": "Ownership", "business_facts": {
        "table_regions": [{"rows": rows}],
    }}]}

    assert validated_topic(source, ranked_report) == "Primary Fund"


def test_horizontal_change_topic_comes_from_its_cited_metric():
    series = {"metric": "Sales", "label_cell": "A2", "points": [
        {"period": "2025-01-01", "period_cell": "B1", "value": 10, "value_cell": "B2"},
        {"period": "2025-02-01", "period_cell": "C1", "value": 20, "value_cell": "C2"},
    ]}
    source = {"sheets": [{"name": "Sales", "business_facts": {
        "horizontal_series": [series],
    }}]}

    assert validated_topic(source, horizontal_trend_report) == "매출(Sales)"


@pytest.mark.parametrize("label", ["SP_ENTITY_NAME", "Value", "ID", "2025-01-01", "=A1+B1"])
def test_machine_or_non_subject_labels_are_not_topics(label):
    assert source_topic(label) is None
