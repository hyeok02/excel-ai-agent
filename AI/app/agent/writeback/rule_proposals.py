"""A proposal built from source-checked rules: every matching row, or nothing."""
from app.agent.writeback.period_columns import unread_years
from app.agent.writeback.models import WritebackProposal, WritebackStatus
from app.agent.writeback.references import key
from app.agent.query.ambiguity_labels import resolve_unique_column
from app.agent.writeback.rule_mentions import UNREAD, unnamed_text_targets, unread_names
from app.agent.writeback.rule_ranks import RANK_WORDS
from app.agent.writeback.rule_execution import RuleNotFound, RuleRejected, RuledTargets, rule_drafts
from app.agent.writeback.validation import validate_changes

PARTIAL = "일부 행만 바뀌지 않도록 이 요청의 변경안을 만들지 않았습니다."


def ruled_proposal(instruction, rules, summary, index):
    """None when a rule names nothing in the source, so the cell drafts are used instead."""
    drafts, readings, headers, offered, copied, tables = [], [], [], [], {}, []
    try:
        for rule in rules:
            found, reading, changed, taken = rule_drafts(rule, summary, index, instruction)
            copied.update(taken)
            drafts.extend((draft, 1 + len(rule.also_target_column_ids)) for draft in found)
            readings.append(reading)
            headers.extend(changed[0])
            offered.extend(changed[1])
            tables.append((changed[2], rule))
    except RuleNotFound:
        return None
    except RuleRejected as error:
        return _blocked(instruction, [str(error)], readings)
    if RANK_WORDS.search(instruction) and not any(rule.rank or rule.average_filters for rule in rules):
        unread = ["‘가장·상위·평균’ 같은 순위"]  # read as a fixed value instead ('단가 = 24,000' for 가장 비싼)
    else:
        unread = unread_names(instruction, tables) or unnamed_text_targets(instruction, tables, resolve_unique_column)
    if unread:
        return _blocked(instruction, [f"{UNREAD} {', '.join(unread[:3])} 조건이 해석에 빠졌습니다. 조건을 다시 확인해 주세요."], readings)
    if (missing := unread_years(instruction, headers, offered)):
        return _blocked(instruction, [f"요청한 기간 중 {', '.join(missing)}년 열이 해석에서 빠졌습니다.", PARTIAL], readings)
    if (drafts := _one_per_cell(drafts)) is None:
        return _blocked(instruction, ["같은 셀에 서로 다른 값을 넣는 해석이 함께 있습니다.", PARTIAL], readings)
    every = {key(cell.sheet_name, cell.address): cell for row in index.rows for cell in row.cells}
    changes, risks = validate_changes(drafts, every, index, instruction, ruled=RuledTargets(instruction, copied))
    if risks or len(changes) != len(drafts):
        return _blocked(instruction, [*dict.fromkeys(risks[:8]), PARTIAL], readings)
    return WritebackProposal(
        instruction=instruction, status=WritebackStatus.READY,
        summary=f"승인 전 확인할 {len(changes)}개 셀 변경안을 준비했습니다.",
        changes=changes, risks=[], limitations=readings)


def _one_per_cell(drafts):
    """Two readings reaching one cell count once when they agree ('교통' and '교통 지출' rows); when they differ,
    the reading aimed at that one column wins over one that also swept it in ('세탁기와 TV를 각각 200, 220')."""
    cells = {}
    for draft, width in drafts:
        cells.setdefault((draft.sheet_name, draft.reference.upper()), []).append((width, draft))
    kept = []
    for group in cells.values():
        narrow = min(width for width, _ in group)
        values = {repr(draft.new_value) for width, draft in group if width == narrow}
        if len(values) > 1:
            return None
        kept.append(next(draft for width, draft in group if width == narrow))
    return kept


def _blocked(instruction, risks, readings):
    # The reading still explains what was tried; there is nothing left to approve.
    readings = [reading.replace(" 승인 전에 대상 행과 열을 확인해 주세요.", "") for reading in readings]
    return WritebackProposal(
        instruction=instruction, status=WritebackStatus.BLOCKED,
        summary="안전하게 적용할 변경 셀을 확인하지 못했습니다.",
        changes=[], risks=risks, limitations=readings)
