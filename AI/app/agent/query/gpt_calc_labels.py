"""How a table calculation's conditions and row formulas read in an answer: 입사일 ≥ 2021-01-01, Qty×UnitPrice."""
import re

from app.agent.query.gpt_calc_planner import column_name


def plain(value):
    return f"{value:,.2f}".rstrip("0").rstrip(".") if not float(value).is_integer() else f"{value:,.0f}"


_SYMBOLS = {"eq": "=", "ne": "≠", "gt": ">", "ge": "≥", "lt": "<", "le": "≤", "contains": "포함:",
            "year": "연도 =", "month": "월 =", "quarter": "분기 =", "under": "구간:"}


def _formula_name(formula, table):
    names = {column.id.upper(): column_name(column) for column in table.columns}
    return re.sub(r"\[([A-Za-z]{1,3})\]", lambda match: names.get(match.group(1).upper(), match.group(0)), formula)


def _condition(item):
    symbol = _SYMBOLS.get(item.op.removesuffix("_column"), item.op)
    value = item.value.strip()
    value = plain(float(value)) if re.fullmatch(r"-?\d+\.\d+", value) else value  # 18.16 from [Table!B66]
    return f"{item.column} {symbol} {value or '빈칸'}"
