"""Source-computed fallbacks shared by ordinary and repaired query execution."""
from app.agent.query.comparison_answers import validated_comparison_answer
from app.agent.query.grouped_change_answers import validated_grouped_change_answer
from app.agent.query.metric_change_answers import validated_metric_change_answer
from app.agent.query.metric_period_answers import validated_metric_period_answer
from app.agent.query.metric_snapshot_answers import validated_metric_snapshot_answer
from app.agent.query.row_list_answers import validated_row_list_answer
from app.agent.query.structure_answers import validated_structure_answer
from app.agent.query.verified_insight_answers import validated_verified_insight_answer
from app.agent.query.workbook_summary_answers import validated_workbook_summary_answer


def canonical_answer(question, execution, truncated, summary, data_index, intent):
    for answerer in (validated_comparison_answer, validated_grouped_change_answer,
                     validated_metric_period_answer, validated_metric_snapshot_answer,
                     validated_metric_change_answer):
        if answer := answerer(question, execution, truncated):
            return answer
    if answer := validated_row_list_answer(question, execution, truncated,
                                           summary=summary, data_index=data_index):
        return answer
    for answerer in (validated_structure_answer, validated_workbook_summary_answer):
        if answer := answerer(question, execution, truncated):
            return answer
    return validated_verified_insight_answer(question, execution, truncated, intent)
