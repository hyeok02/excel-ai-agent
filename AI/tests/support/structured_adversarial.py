"""Source-bound compound plans used by service and HTTP regression tests."""
from app.agent.query.boolean_filter_language import parse_boolean
from app.agent.query.composite_models import CompositeQueryPlan, CompositeQuestionPart
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.support.large_workbook_fixtures import parsed, workbook


def source():
    return parsed(workbook({"Records": [
        ["Record", "Region", "Status", "Amount", "Costs"],
        ["Alpha", "North", "Open", 10, 100], ["Beta", "South", "Closed", 20, 200],
        ["Gamma", "West", "Open", 30, 300], ["Delta", "South", "Open", 40, 400],
    ]}))


def plan(summary, *, statistic="sum", column="D", condition="", table=None):
    table = table or build_query_tables(summary)[0]
    parsed = parse_boolean(condition, table) if condition else None
    return TabularQueryPlan(operation="numeric_summary", table_id=table.id,
        column_ids=[column], statistic=statistic, filters=parsed.filters if parsed else [],
        filter_expression=parsed.expression if parsed else None)


def compound(parts, plans, prefix=""):
    return QuestionIntent(False, from_model=True, composite_query=CompositeQueryPlan(
        shared_prefix=prefix, parts=[CompositeQuestionPart(source_text=text, kind="aggregation",
            tabular_query=query) for text, query in zip(parts, plans)]))
