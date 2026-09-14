from app.services.insights.narratives.horizontal_trends import horizontal_trend_report
from app.services.insights.narratives.table_narratives import _numeric
from app.services.insights.narratives.trend_narratives import _related_topic, trend_report
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.prompts import SYSTEM_PROMPT
from app.services.insights.quality import _change_insight
from app.services.insights.verification.validator import validate_workbook_insights
from app.services.insights.verification.validator import _validate_insight
from app.services.insights.verification.validation_index import workbook_evidence_index
from tests.support.narrative_contexts import source_records, trend_context


def test_three_observations_are_a_trend_but_component_comparisons_are_changes():
    items, _ = trend_report(trend_context())

    assert [item.category for item in items] == ["trend", "change"]
    assert "2025년 2월 1일" in items[0].fact
    assert "2025년 2월 1일" not in items[1].fact
    assert items[0].topic == "전체 인원"
    assert items[1].topic == "운영 부문·기획 부문"
    assert items[1].title == "운영 부문·기획 부문 변화"


def test_common_source_axis_is_used_in_component_title():
    context = trend_context(("전체 인원", "부서 > 기획", "부서 > 운영"))

    items, _ = trend_report(context)

    assert items[1].title == "부서별 전체 인원 변화"
    assert items[1].topic == "부서별 전체 인원"


def test_mixed_source_axes_are_named_without_guessing_the_unlabelled_item():
    context = trend_context((
        "Total Employees", "Department > General & Administrative", "Analyst",
    ))

    items, _ = trend_report(context)

    assert items[0].topic == "전체 직원 수"
    assert items[1].topic == "부서 등 항목별 전체 직원 수"
    assert items[1].title == "부서 등 항목별 전체 직원 수 변화"


def test_distinct_axes_can_form_a_bounded_topic():
    related = [
        {"metric": "Department > General & Administrative"},
        {"metric": "Roles > Legal"},
        {"metric": "Analyst"},
    ]

    assert _related_topic("전체 직원 수", related) == "부서·직무 등 항목별 전체 직원 수"


def test_unsubstantiated_model_topic_is_not_shown():
    context = trend_context()
    items, _ = trend_report(context)
    invented = items[0].model_copy(update={"topic": "외계 회사의 매출"})

    validated = _validate_insight(invented, workbook_evidence_index(context), items)

    assert validated is not None
    assert validated.topic is None


def test_source_derived_topics_survive_validation():
    context = trend_context()
    items, _ = trend_report(context)

    report = validate_workbook_insights(
        WorkbookInsightReport(overview="", insights=items), context,
    )

    assert [item.topic for item in report.insights[:2]] == [
        "전체 인원", "운영 부문·기획 부문",
    ]


def test_two_observations_are_a_change_not_a_trend():
    context = trend_context()
    source_records(context).pop(2)

    items, _ = trend_report(context)

    assert [item.category for item in items] == ["change", "change"]
    assert "기간별 기록은" not in items[0].fact

    report = validate_workbook_insights(
        WorkbookInsightReport(overview="", insights=items), context,
    )
    assert report.overview.startswith("이 파일은 푸른연구원의 전체 인원 변동을 다룹니다.")


def test_fallback_two_point_comparison_is_change():
    change = trend_context()["sheets"][0]["business_facts"]["numeric_changes"][0]

    assert _change_insight(None, change).category == "change"


def test_horizontal_endpoint_only_fact_is_a_change_even_with_three_source_points():
    points = [
        {"period": f"2025-0{month}-01", "period_cell": f"{column}1",
         "value": value, "value_cell": f"{column}2"}
        for month, column, value in ((1, "B", 100), (2, "C", 90), (3, "D", 80))
    ]
    context = {"sheets": [{"name": "Data", "business_facts": {
        "horizontal_series": [{"metric": "Revenue", "label_cell": "A2", "points": points}],
    }}]}

    items, _ = horizontal_trend_report(context)

    assert items[0].category == "change"
    assert "2025년 2월 1일" not in items[0].fact


def test_date_table_min_max_is_a_metric_not_a_trend():
    label = {"cell": "A2", "value": "열량"}
    values = [
        ({"cell": f"{column}1", "value": f"2025-0{month}-01"},
         {"cell": f"{column}2", "value": value})
        for month, column, value in ((1, "B", 700), (2, "C", 740), (3, "D", 720))
    ]

    item = _numeric("Data", label, values)

    assert item.category == "metric"
    assert item.title == "열량의 날짜별 값 범위"
    assert "가장 낮은 날" in item.fact and "가장 높은 날" in item.fact


def test_prompt_reserves_trend_for_visible_three_point_trajectory():
    assert "시작·종료 시점 비교나 항목별 증감이면 change" in SYSTEM_PROMPT
    assert "관측값이 3개 이상이고 fact에 중간 시점까지" in SYSTEM_PROMPT
