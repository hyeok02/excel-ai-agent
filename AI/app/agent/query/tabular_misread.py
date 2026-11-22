"""A table plan whose result cannot be what was asked, read from the plan and the rows, not from words.

Such a plan is not answered: the question goes on to the calculation that reads the whole table.
- A summary of one row column by column ("전환율 6개월 평균" read as 1월 평균 17.6%, 2월 평균 14.4% …):
  a sum or mean over a single value per column answers nothing.
- The top row shown by values that do not tell rows apart ("출고가 가장 많았던 날" as one item's row
  on a day three items share): the largest row is not the largest day.
- A part of the year ("4분기", "상반기") read from a column that is no month of a table laid out by months
  ("합계"): the whole year's figure, not the part asked.
"""
import re

_MONTH = re.compile(r"\s*(?:1[0-2]|[1-9])\s*월\s*|\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*",
                    re.I)
_PART_OF_YEAR = re.compile(r"[1-4]\s*분기|[상하]\s*반기|\b[QH][1-4]\b|\b(?:first|second|third|fourth)\s+quarter\b", re.I)


def misread(question, plan, table, rows, shown_rows, selected):
    """Why the plan's result does not answer the question, or None."""
    if plan.operation == "numeric_summary" and not plan.group_by and len(rows) == 1 and len(selected) > 1:
        return "one row summarized column by column"
    if plan.order_by and plan.limit and not plan.group_by and len(shown_rows) < len(rows):
        # Only labels every row fills: a sector named once over its subsectors is an outline, read elsewhere.
        labels = [key for key in selected if key != plan.order_by and all(
            row.values.get(key) not in (None, "") and not isinstance(row.values.get(key), (int, float)) for row in rows)]
        if labels and len({tuple(row.values.get(key) for key in labels) for row in rows}) < len(rows):
            return "the top row is shown by values other rows share"
    months = {column.id for column in table.columns if _MONTH.fullmatch(str(column.header))}
    if len(months) >= 3 and _PART_OF_YEAR.search(question) and not set(selected) & months:
        return "a part of the year read from a column that is no month"
    return None
