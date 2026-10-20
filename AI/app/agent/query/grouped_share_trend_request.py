"""Bind part/whole orientation while protecting actual source field names."""
import re

from app.agent.query.derived_trend_request import calculation_question
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.trend_labels import trend_label_spellings

TOTAL = re.compile(r"전체|총(?=\s|__|[가-힣])|\b(?:total|all|overall)\b", re.I)


def protect_headers(question, tables):
    fields = {spelling for table in tables for column in table.columns
              for spelling in trend_label_spellings(column.header)}
    masked, replacements = question, {}
    for field in sorted(fields, key=len, reverse=True):
        marker = f"__field{len(replacements)}__"
        pattern = r"(?<![a-z0-9])" + re.escape(field) + r"(?![a-z0-9])"
        updated = re.sub(pattern, marker, masked, flags=re.I)
        if updated != masked:
            replacements[marker] = field
            masked = updated
    return masked, replacements


def restore_headers(question, replacements):
    for marker, field in replacements.items():
        question = question.replace(marker, field)
    return question


def clean_share_question(question, tables):
    masked, replacements = protect_headers(question, tables)
    return restore_headers(calculation_question(masked), replacements), masked


def whole_relation(question, source, target):
    masked, _ = protect_headers(question, [source.table])
    categories = value_matches(masked, target.value)
    if len(categories) != 1:
        raise ValueError("비중을 구할 하나의 범주를 명확하게 지정해 주세요.")
    category = categories[0]
    # A category called 'Total' does not establish a whole-population operator.
    masked = masked[:category.start()] + " " * len(category[0]) + masked[category.end():]
    wholes = list(TOTAL.finditer(masked))
    if len(wholes) != 1:
        raise ValueError("동일 표의 전체 합계를 분모로 지정해 주세요. 항목명 속 Total은 전체 분모 조건으로 보지 않았습니다.")
    whole = wholes[0]
    if whole.end() < category.start():
        bridge = masked[whole.end():category.start()]
        valid = re.search(r"중(?:에서)?|대비", bridge)
    elif category.end() < whole.start():
        bridge = masked[category.end():whole.start()]
        valid = re.search(r"\b(?:share|proportion|percentage|ratio)\s+of\s+(?:the\s+)?$", bridge, re.I)
    else:
        valid = False
    if not valid:
        raise ValueError("범주 비중의 분자·분모 방향을 확정하지 못했습니다. '전체 수치 중 대상 범주의 비중'으로 지정해 주세요.")


def remove_whole(question, table):
    masked, replacements = protect_headers(question, [table])
    return restore_headers(TOTAL.sub(" ", masked), replacements)
