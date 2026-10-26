"""Explicit test planner proposals, not a natural-language interpretation oracle.

The public API must independently verify these plans against each question and
workbook. Values are calculated by production code, never supplied by this fake.
"""
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.relational_models import RelationalQueryPlan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan


class CapabilityPlanner:
    def __init__(self, case_id):
        self.case_id = case_id

    async def classify(self, question, summary):
        tables = {table.sheet_name: table for table in build_query_tables(summary)}
        if self.case_id.startswith("join_"):
            lookup = self.case_id == "join_lookup"
            plan = RelationalQueryPlan(
                operation="lookup" if lookup else "numeric_summary",
                left_table_id=tables["Orders"].id, right_table_id=tables["Customers"].id,
                on=[{"left_column_id": "B", "right_column_id": "A"}],
                column_ids=["right.B", "left.C"], group_by=[] if lookup else ["right.B"],
                filters=[{"side": "left", "column_id": "A", "operator": "equals",
                          "value": "ORD-2"}] if lookup else [],
            )
            return QuestionIntent(False, "cell_lookup" if lookup else "aggregation",
                                  from_model=True, relational_query=plan)
        if self.case_id in ("resolved_scope", "formula_aggregate"):
            sheet = "South" if self.case_id == "resolved_scope" else "Calculations"
            column = "B" if sheet == "South" else "D"
            plan = TabularQueryPlan(operation="numeric_summary", table_id=tables[sheet].id,
                                    column_ids=[column], statistic="sum")
            return QuestionIntent(False, "aggregation", from_model=True, tabular_query=plan)
        return QuestionIntent.from_keywords(question)
