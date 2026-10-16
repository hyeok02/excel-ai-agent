"""Planning instructions for source-addressed cross-table questions."""

RELATIONAL_PROMPT = """
When a question requires joining two distinct catalog tables, populate relational_query
and leave tabular_query null. Never join merely because two sheets have similar numbers.
Use exact catalog table IDs. on contains 1–4 exact left_column_id/right_column_id pairs;
use the complete natural key, including date/company/entity components where necessary.
Right-side keys must be unique for keys used by the chosen left population;
duplicates outside that population do not invalidate a scoped lookup. Many-to-many joins are refused.
column_ids and group_by use qualified references such as left.B/right.F, never guessed
cell coordinates. Supported operations: lookup, row_list, row_count, numeric_summary.
numeric_summary supports statistic sum/average/min/max and optional group_by.
For numeric_summary, column_ids contains only numeric measures to calculate;
group_by contains grouping labels and must not be duplicated in column_ids.
Choose the detail/fact rows as left, unique lookup/dimension rows as right. An aggregate
of right-side values repeated across multiple left rows is refused to prevent inflation.
Every left/right predicate must be explicitly requested; use typed filters with side.
population=all_left preserves every selected left row; join_type=left is the default.
Only use population=matched_only when the user explicitly asks for matching/common rows.
Never invent matched_only to hide missing records. Null keys never match each other;
left joins retain those rows as unmatched and keep unresolved groups explicitly separate.
No implicit string/number coercion, missing source amount, or uncalculated formula
may be treated as a zero. Unresolved group membership is not a guessed real category.
Headers with different names require the question to specify both join keys. If the join
key or record population is unclear, do not create a guessed relational plan.
Relational execution returns source_checked, not request_checked: source and arithmetic
checks do not independently prove all model-interpreted business relationship semantics.
"""
