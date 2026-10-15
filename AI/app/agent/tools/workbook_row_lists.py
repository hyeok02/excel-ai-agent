"""조건에 맞는 행을 골라 그 이름을 모은다.

"네트워크가 불안정한 장비는?" 같은 질문은 셀 하나를 읽어 끝나지 않고, 한 열을
훑어 조건에 맞는 행의 이름을 나열해야 한다. 모델에게 맡기면 셀을 빠뜨리거나
없는 이름을 지어내고, 그러면 검증에서 답변이 통째로 버려진다. 코드가 직접
세어 두면 모델이 어떻게 쓰든 답이 나온다.
"""
from app.agent.query.index import IndexedRow
from app.agent.query.interpretation_answers import asks_interpretation
from app.agent.tools.workbook_headers import HeaderContext, header_for
from app.agent.tools.workbook_label_choice import label_column
from app.agent.tools.workbook_label_columns import column_of
from app.agent.tools.workbook_row_conditions import (
    NEGATIVE_MARKS,
    POSITIVE_MARKS,
    requested_condition,
)
from app.services.insights.facts.flag_columns import mark_of

MIN_LISTED_ROWS = 1
MAX_LISTED_ROWS = 40


def build_row_list(
    rows: list[IndexedRow], headers: HeaderContext, question: str
) -> dict[str, object] | None:
    if asks_interpretation(question):
        return None  # A list of marks cannot answer a causal or semantic question.
    found = requested_condition(question, rows, headers)
    if found is None:
        return None
    sheet_name, column, header, header_reference, polarity = found
    wanted = NEGATIVE_MARKS if polarity == "negative" else POSITIVE_MARKS
    label = label_column(rows, headers, sheet_name, column, question)
    if label is None:
        return None
    name_column, label_header, label_reference = label
    matches, others, blank = [], 0, 0
    for row in sorted(rows, key=lambda item: item.row_number):
        if row.sheet_name != sheet_name:
            continue
        cell = _cell(row, column)
        name = _cell(row, name_column)
        if (cell is not None and cell.reference == header_reference) or (
            name is not None and name.reference == label_reference
        ):
            continue
        if name is None or not str(getattr(name, "value", "") or "").strip():
            continue
        if cell is None or not str(cell.value or "").strip():
            blank += 1
            continue
        if mark_of(cell.value) in wanted:
            matches.append({
                "label": str(name.value).strip(),
                "label_reference": name.reference,
                "value": cell.value,
                "value_reference": cell.reference,
            })
        else:
            others += 1
    if not MIN_LISTED_ROWS <= len(matches) <= MAX_LISTED_ROWS:
        return None
    return {
        "sheet_name": sheet_name,
        "header": header,
        "header_reference": header_reference,
        "label_header": label_header,
        "label_reference": label_reference,
        "polarity": polarity,
        "matches": matches,
        "other_count": others,
        "blank_count": blank,
    }


def _cell(row: IndexedRow, column: str):
    for cell in row.cells:
        if column_of(cell.address) == column:
            return cell
    return None
