import re

from app.agent.query.index import WorkbookDataIndex
from app.agent.writeback.candidates import select_writeback_candidates
from app.agent.writeback.models import (
    WritebackChange,
    WritebackGenerator,
    WritebackProposal,
    WritebackStatus,
)

CELL_REFERENCE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]{0,6}$")


class WorkbookWritebackProposalService:
    def __init__(self, generator: WritebackGenerator) -> None:
        self._generator = generator

    async def propose(
        self, instruction: str, data_index: WorkbookDataIndex
    ) -> WritebackProposal:
        available = {
            _key(cell.sheet_name, cell.address): cell
            for row in data_index.rows
            for cell in row.cells
        }
        candidates = select_writeback_candidates(instruction, data_index)
        context = {
            "truncated": data_index.truncated,
            "cells": [
                {
                    "sheet_name": cell.sheet_name,
                    "reference": cell.address,
                    "value": cell.value,
                    "formula": cell.formula,
                }
                for cell in candidates
            ],
        }
        draft = await self._generator.generate(instruction, data_index.filename, context)
        changes, risks = _validate_changes(draft.changes, available)
        limitations = list(draft.limitations)
        if data_index.truncated:
            limitations.append("대용량 워크북의 일부 셀은 변경 후보 검색에서 제외되었습니다.")
        if not draft.changes:
            limitations.append("지시에서 안전하게 특정할 변경 셀을 찾지 못했습니다.")
        ready = bool(changes) and not risks and len(changes) == len(draft.changes)
        return WritebackProposal(
            instruction=instruction,
            status=WritebackStatus.READY if ready else WritebackStatus.BLOCKED,
            summary=draft.summary,
            changes=changes if ready else [],
            risks=list(dict.fromkeys(risks)),
            limitations=list(dict.fromkeys(limitations)),
        )


def _validate_changes(drafts, available) -> tuple[list[WritebackChange], list[str]]:
    changes, risks, seen = [], [], set()
    for draft in drafts:
        reference = draft.reference.strip().upper()
        key = _key(draft.sheet_name, reference)
        cell = available.get(key)
        if not CELL_REFERENCE.fullmatch(reference) or cell is None:
            risks.append(f"{draft.sheet_name}!{reference}: 원본에서 확인할 수 없는 셀입니다.")
            continue
        if key in seen:
            risks.append(f"{draft.sheet_name}!{reference}: 중복 변경입니다.")
            continue
        seen.add(key)
        if cell.formula:
            risks.append(f"{draft.sheet_name}!{reference}: 수식 셀은 수정할 수 없습니다.")
            continue
        if isinstance(draft.new_value, str) and draft.new_value.lstrip().startswith("="):
            risks.append(f"{draft.sheet_name}!{reference}: 새 수식 입력은 허용하지 않습니다.")
            continue
        if draft.new_value == cell.value:
            risks.append(f"{draft.sheet_name}!{reference}: 기존 값과 동일합니다.")
            continue
        payload = draft.model_dump()
        payload["reference"] = reference
        changes.append(WritebackChange(**payload, old_value=cell.value))
    return changes, risks


def _key(sheet_name: str, reference: str) -> str:
    return f"{sheet_name.casefold()}!{reference.upper()}"
