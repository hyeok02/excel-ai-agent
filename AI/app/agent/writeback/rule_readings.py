"""The sentence a reviewer reads before approving a rule: which rows, which columns, what change."""
from app.agent.writeback.display_values import exact
from app.agent.writeback.references import key
from app.agent.writeback.rounding_words import rounding_places
from app.agent.writeback.rule_columns import comparison_text
from app.agent.writeback.rule_ranks import rank_text
from app.agent.writeback.rule_rows import shown as condition_value

OPERATIONS = {"set": "{amount}(으)로 바꾸는", "clear": "비우는",
              "percent_increase": "{amount}% 올리는", "percent_decrease": "{amount}% 내리는",
              "add": "{amount}만큼 늘리는", "subtract": "{amount}만큼 줄이는", "multiply": "{amount}배로 바꾸는",
              "prepend_text": "맨 앞에 ‘{amount}’을 붙이는", "append_text": "맨 뒤에 ‘{amount}’을 붙이는",
              "replace_text": "글자 중 ‘{find}’을 ‘{amount}’(으)로 바꾸는", "round": "{places} 반올림하는",
              "round_up": "{places} 올림하는", "round_down": "{places} 내림하는"}
UNITS = {"days": "일", "weeks": "주", "months": "개월", "years": "년"}
OPERATORS = {"equals": "=", "not_equals": "≠", "contains": "포함", "greater_than": ">",
             "greater_than_or_equal": "≥", "less_than": "<", "less_than_or_equal": "≤",
             "is_blank": "빈칸", "not_blank": "빈칸 아님"}


def rule_reading(rule, table, picked, drafts, cells, resolve, instruction=""):
    """picked: (filters, comparisons, rows, targets, source, other row note)."""
    filters, comparisons, rows, targets, source, other = picked
    columns = {column.id: column for column in table.columns}
    conditions = ", ".join(filter(None, [
        *(f"‘{columns[item.column_id].display_header}’ {OPERATORS[item.operator]} {condition_value(item.value)}".rstrip()
          for item in filters),
        *(comparison_text(item, columns) for item in comparisons), rank_text(rule, columns, resolve, table)]))
    # A value to set reads as the cells will show it: 0.013 in a 0.0% column is 1.3%.
    shown_values = {exact(draft.new_value, getattr(cells.get(key(table.sheet_name, draft.reference)), "number_format",
                                                   "General")) for draft in drafts} if rule.operation == "set" and source is None else set()
    amount = shown_values.pop() if len(shown_values) == 1 and None not in shown_values else rule.amount
    if source is not None:
        action = f"같은 행의 ‘{columns[source].display_header}’ 값으로 바꾸는"
    elif other:
        action = f"{other}(으)로 바꾸는"
    elif rule.amount_unit:
        action = f"{rule.amount}{UNITS[rule.amount_unit]} {'늦추는' if rule.operation == 'add' else '앞당기는'}"
    else:
        action = OPERATIONS[rule.operation].format(amount=amount, find=rule.find_text, places=_places(rule.amount, instruction))
    scope = f"‘{table.sheet_name}’ 표에서 {conditions}인" if conditions else f"‘{table.sheet_name}’ 표 전체"
    headers = [columns[target].display_header for target in targets]
    return (f"{scope} {len(rows)}개 행의 {_named(headers)} 값을 "
            f"{action} 것으로 해석했습니다 ({rule.reading}). 승인 전에 대상 행과 열을 확인해 주세요.")


def _places(amount, instruction):
    stated = rounding_places(instruction)
    places = next(iter(stated)) if len(stated) == 1 else int(amount) if str(amount).lstrip("-").isdigit() else 0
    return f"소수 {places}자리로" if places > 0 else "정수로" if places == 0 else f"{10 ** -places:,} 단위로"


def _named(headers):
    if len(headers) <= 4:
        return ", ".join(f"‘{header}’" for header in headers)
    return f"‘{headers[0]}’ 등 {len(headers)}개 열({', '.join(headers)})"
