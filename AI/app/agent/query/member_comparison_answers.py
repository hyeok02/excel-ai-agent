"""Compare two or more named members on one measure, computed from every source row.

"Boston과 Los Angeles 판매금액 차이는?" is read by the model as a comparison of the City values
Boston and Los Angeles on TotalPrice, with no plan: nothing compared them, and the draft fell back
to two single sales. Here each member's total is computed from all rows of the one table holding
them; "웨일스 인구가 스코틀랜드보다 많아?" names two columns of a table, read on its one total row.
The model's reading of the names is stated; anything not found exactly in one table stays as it was.
"""
from decimal import Decimal

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.natural_relative_ranking import natural_relative_answer
from app.agent.query.ranked_group_units import shown_total, total_unit
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_translated_names import _TOTAL

MAX_EVIDENCE = 40


def relative_or_compared(question, summary, index, intent):
    return natural_relative_answer(question, summary, index, intent) or member_comparison_answer(question, summary, index, intent)


def member_comparison_answer(question, summary, index, intent):
    targets = list(dict.fromkeys(_normal(item) for item in getattr(intent, "targets", ()) if _normal(item)))
    if (intent.kind != "comparison" or intent.tabular_query is not None or intent.relational_query is not None
            or intent.whole_workbook or len(targets) < 2 or summary is None or index is None):
        return None
    tables = [table for table in build_query_tables(summary) if table.complete and table.rows]
    found = [*_by_rows(tables, targets), *_by_columns(tables, targets)]
    if len(found) != 1:
        return None  # nothing, or the names fit more than one table: the comparison is not one reading
    table, members, header, cells, values, unit, reading = found[0]
    ordered = sorted(members, key=lambda member: values[member], reverse=True)
    listed = ", ".join(f"{member} {shown_total(values[member], unit)}" for member in members)
    first, second = ordered[0], ordered[1]
    gap = values[first] - values[second]
    verdict = (f"{', '.join(members)}의 값이 같습니다." if gap == 0 and len(members) == 2 else
               f"{first} 쪽이 {second}보다 {shown_total(gap, unit)} 많습니다." if len(members) == 2 else
               f"가장 큰 값은 {first}입니다.")
    source = {cell.reference: cell for row in index.rows if row.sheet_name == table.sheet_name for cell in row.cells}
    return QuestionAnswer(
        question=question, answer=f"{header}: {listed}.\n{verdict}", status=QuestionAnswerStatus.LIMITED,
        confidence=0.8, selected_tools=["member_comparison"],
        evidence=[_evidence(source[key]) for key in dict.fromkeys(cells) if key in source][:MAX_EVIDENCE],
        limitations=[f"질문의 대상 해석: {reading}. 원본 전체 행에서 계산했습니다."],
        verification=QuestionAnswerVerification(level="source_checked",
                                                checks=["source_values", "calculation", "comparison", "field_interpretation"]))


def _by_rows(tables, targets):
    """Members are values of one text column; the measure is a numeric column a target names."""
    for table in tables:
        headers = {_normal(column.header): column for column in table.columns}
        measures = [headers[target] for target in targets if target in headers and _numeric(table, headers[target].id)]
        for column in table.columns:
            names = {_normal(row.values.get(column.id)): row.values.get(column.id) for row in table.rows
                     if isinstance(row.values.get(column.id), str)}
            members = [names[target] for target in targets if target in names]
            if len(members) < 2 or len(measures) != 1 or measures[0].id == column.id:
                continue
            measure, totals, cells = measures[0], {member: Decimal(0) for member in members}, []
            for row in table.rows:
                name, value = row.values.get(column.id), row.values.get(measure.id)
                if name in totals and value not in (None, ""):
                    if not _number(value):
                        break  # a non-numeric amount is never skipped silently
                    totals[name] += Decimal(str(value))
                    cells += [f"{table.sheet_name}!{_letter(column)}{row.row_number}", f"{table.sheet_name}!{_letter(measure)}{row.row_number}"]
            else:
                yield (table, members, f"‘{column.display_header}’별 ‘{measure.display_header}’ 합계",
                       [column.header_reference, measure.header_reference, *cells], totals, total_unit(table, measure.id),
                       f"‘{column.display_header}’ = {', '.join(members)}, 항목 ‘{measure.display_header}’")


def _by_columns(tables, targets):
    """Members are numeric columns of a table; they are read on its one total row ("All Persons")."""
    for table in tables:
        columns = [column for column in table.columns if _normal(column.header) in targets]
        if len(columns) < 2 or len(columns) != len(targets):
            continue
        labels = [(row, value) for row in table.rows for column in table.columns
                  if isinstance(value := row.values.get(column.id), str) and _TOTAL.fullmatch(value.strip())]
        if len(labels) != 1:
            continue
        row, label = labels[0]
        if not all(_number(row.values.get(column.id)) for column in columns):
            continue
        members = [" ".join(column.header.split()) for column in columns]
        values = {member: Decimal(str(row.values[column.id])) for member, column in zip(members, columns)}
        cells = [reference for column in columns
                 for reference in (column.header_reference, f"{table.sheet_name}!{_letter(column)}{row.row_number}")]
        yield (table, members, f"‘{label.strip()}’ 행", cells, values, ("", ""), f"열 {', '.join(members)}의 ‘{label.strip()}’ 행")


def _numeric(table, column_id):
    values = [row.values.get(column_id) for row in table.rows if row.values.get(column_id) not in (None, "")]
    return bool(values) and all(_number(value) for value in values)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _letter(column):
    return "".join(character for character in column.header_reference.rsplit("!", 1)[-1] if character.isalpha())


def _normal(value):
    return " ".join(str(value or "").split()).casefold()
