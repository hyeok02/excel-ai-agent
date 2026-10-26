"""Authorize natural destinations by intersecting source row and column labels."""
import re
from collections import defaultdict

from app.agent.writeback.references import column_number
from app.agent.writeback.natural_operations import ASSIGNMENT
from app.agent.writeback.target_syntax import sheet_mentions

ALL = re.compile(r"모두|전체|각각|모든|\ball\b|\bevery\b", re.I)


def semantic_target_risk(cell, instruction, index, headers) -> str | None:
    sheets = {row.sheet_name for row in index.rows}
    named = {name for _, _, name in sheet_mentions(instruction, sheets)}
    if named and cell.sheet_name not in named:
        return "요청에 명시한 시트와 변경 대상 시트가 다릅니다."
    # Replacement labels must never authorize another source row.
    prefix = ASSIGNMENT.split(instruction, maxsplit=1)[0]
    matches = []
    for row in index.rows:
        if named and row.sheet_name not in named:
            continue
        labels = [item for item in row.cells if _label_matches(item.value, prefix)]
        if labels:
            matches.append((row, labels, _data_row(row, headers)))
    source_labels = {str(item.value).casefold() for _, labels, data in matches if data for item in labels}
    matched_sheets = {sheet for sheet in sheets if source_labels <= {
        str(item.value).casefold() for row, labels, data in matches
        if data and row.sheet_name == sheet for item in labels
    }} if source_labels else {row.sheet_name for row, _, _ in matches}
    if not matches:
        return "요청한 변경 항목을 원본의 행·열 이름과 대조하지 못했습니다. 시트·셀을 지정해 주세요."
    if cell.sheet_name not in matched_sheets:
        return "요청한 원본 항목이 있는 시트와 변경 대상 시트가 다릅니다."
    if not named and len(matched_sheets) > 1:
        return "같은 원본 항목이 여러 시트에 있어 변경할 시트를 지정해야 합니다."
    local = [(row, labels, data) for row, labels, data in matches if row.sheet_name == cell.sheet_name]
    row_number = int(re.search(r"\d+", cell.address).group())
    if row_number in headers.header_rows.get(cell.sheet_name, set()) and _label_matches(cell.value, prefix):
        same_labels = [item for _, labels, _ in local for item in labels if item.value == cell.value]
        if not any(data for _, _, data in local) and len(same_labels) == 1:
            return None
        return "같은 머리글 또는 행 조건이 함께 있어 수정할 머리글 셀을 지정해야 합니다."
    prior_headers = sorted(number for number in headers.header_rows.get(cell.sheet_name, set())
                           if number < row_number)
    band = {prior_headers[-1]} if prior_headers else set()
    for number in reversed(prior_headers[:-1]):
        if number + 1 in band:
            band.add(number)
    columns = {column_number(item.address) for row, labels, data in local
               if not data and row.row_number in band for item in labels}
    if any(not data for _, _, data in local) and not columns:
        return "요청한 열 이름이 변경 대상 행의 원본 표 머리글과 일치하지 않습니다."
    constraints = defaultdict(set)
    signatures = defaultdict(set)
    for row, labels, data in local:
        if data:
            for item in labels:
                column = column_number(item.address)
                constraints[column].add(row.row_number)
                signatures[row.row_number].add((column, str(item.value).casefold()))
    rows = set.intersection(*constraints.values()) if constraints else set()
    # A named dimension qualifies the row; it is not another metric destination.
    if columns - constraints.keys():
        columns -= constraints.keys()
    if constraints and row_number not in rows:
        return "요청한 모든 항목 조건의 원본 행과 변경 대상 행이 다릅니다."
    if _unknown_subject(prefix, local, named):
        return "요청한 행 조건을 원본 항목과 대조하지 못했습니다. 대상 이름 또는 셀을 확인해 주세요."
    if columns and column_number(cell.address) not in columns:
        return "요청한 항목의 원본 열과 변경 대상 열이 다릅니다."
    if not _all_rows_requested(prefix, local, named):
        if rows and sum(signatures[number] == signatures[row_number] for number in rows) > 1:
            return "같은 항목이 여러 원본 행에 있어 추가 조건 또는 전체 적용 여부를 지정해야 합니다."
        if columns and not rows:
            possible = [row for row in index.rows if row.sheet_name == cell.sheet_name
                        and _data_row(row, headers)
                        and any(column_number(item.address) in columns for item in row.cells)]
            if len(possible) > 1:
                return "요청한 열에 여러 항목이 있어 변경할 행 또는 전체 적용 여부를 지정해야 합니다."
    if not columns:
        source_row = next(row for row in index.rows
                          if row.sheet_name == cell.sheet_name and row.row_number == row_number)
        values = [item for item in source_row.cells if isinstance(item.value, (int, float)) or item.formula]
        if cell in values and len(values) > 1:
            return "요청한 행에 여러 값이 있어 변경할 열 또는 셀을 지정해야 합니다."
        if cell not in values and not _label_matches(cell.value, prefix):
            return "요청한 원본 항목과 변경할 텍스트 셀이 일치하지 않습니다."
    return None


def _data_row(row, headers):
    known = headers.header_rows.get(row.sheet_name, set())
    return row.row_number not in known if known else any(
        isinstance(item.value, (int, float)) or item.formula for item in row.cells
    )


def _label_matches(value, instruction):
    if not isinstance(value, str) or len(value.strip()) < 2:
        return False
    pattern = r"\s*".join(re.escape(part) for part in value.strip().split())
    # Latin identifiers must match whole words: Sales is not Salesforce.
    return bool(re.search(rf"(?<![A-Za-z0-9_]){pattern}(?![A-Za-z0-9_])", instruction, re.I))


def _unknown_subject(prefix, local, named):
    labels = {*named, *(str(item.value) for _, matched, _ in local for item in matched)}
    for label in sorted(labels, key=len, reverse=True):
        prefix = re.sub(re.escape(label), " ", prefix, flags=re.I)
    prefix = re.sub(r"\b(?:set|change|update|the|values?|of|in|sheet|row|column|please|all|every|and|or)\b", " ", prefix, flags=re.I)
    prefix = re.sub(r"원본|현재|기존|항목|시트|모든|모두|전체|각각|수정|변경|바꿔|그리고|또는|에서|으로|값|열|행|의|은|는|을|를|에|만|와|과|및", " ", prefix)
    return any(not any(token.casefold() in name.casefold() for name in named)
               for token in re.findall(r"[A-Za-z0-9가-힣]+", prefix))


def _all_rows_requested(prefix, local, named):
    # Quantifiers inside replacement values or source names are not row authority.
    labels = {*named, *(str(item.value) for _, matched, _ in local for item in matched)}
    for label in sorted(labels, key=len, reverse=True):
        prefix = re.sub(re.escape(label), " ", prefix, flags=re.I)
    return bool(ALL.search(prefix))
