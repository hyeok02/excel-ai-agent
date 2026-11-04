"""A proposal built from source-checked rules: every matching row, or nothing."""
from app.agent.writeback.models import WritebackProposal, WritebackStatus
from app.agent.writeback.references import key
from app.agent.writeback.rule_execution import RuleNotFound, RuleRejected, rule_drafts
from app.agent.writeback.validation import validate_changes

PARTIAL = "일부 행만 바뀌지 않도록 이 요청의 변경안을 만들지 않았습니다."


def ruled_proposal(instruction, rules, summary, index):
    """None when a rule names nothing in the source, so the cell drafts are used instead."""
    drafts, readings = [], []
    try:
        for rule in rules:
            found, reading = rule_drafts(rule, summary, index)
            drafts.extend(found)
            readings.append(reading)
    except RuleNotFound:
        return None
    except RuleRejected as error:
        return _blocked(instruction, [str(error)], readings)
    every = {key(cell.sheet_name, cell.address): cell for row in index.rows for cell in row.cells}
    changes, risks = validate_changes(drafts, every, index, instruction, ruled=True)
    if risks or len(changes) != len(drafts):
        return _blocked(instruction, [*dict.fromkeys(risks[:8]), PARTIAL], readings)
    return WritebackProposal(
        instruction=instruction, status=WritebackStatus.READY,
        summary=f"승인 전 확인할 {len(changes)}개 셀 변경안을 준비했습니다.",
        changes=changes, risks=[], limitations=readings)


def _blocked(instruction, risks, readings):
    # The reading still explains what was tried; there is nothing left to approve.
    readings = [reading.replace(" 승인 전에 대상 행과 열을 확인해 주세요.", "") for reading in readings]
    return WritebackProposal(
        instruction=instruction, status=WritebackStatus.BLOCKED,
        summary="안전하게 적용할 변경 셀을 확인하지 못했습니다.",
        changes=[], risks=risks, limitations=readings)
