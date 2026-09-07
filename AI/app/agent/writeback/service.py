from app.agent.query.index import WorkbookDataIndex
from app.agent.writeback.candidates import select_writeback_candidates
from app.agent.writeback.models import (
    WritebackGenerator,
    WritebackProposal,
    WritebackStatus,
)
from app.agent.writeback.references import MAX_CHANGES, key
from app.agent.writeback.validation import validate_changes


class WorkbookWritebackProposalService:
    def __init__(self, generator: WritebackGenerator) -> None:
        self._generator = generator

    async def propose(
        self, instruction: str, data_index: WorkbookDataIndex
    ) -> WritebackProposal:
        candidates = select_writeback_candidates(instruction, data_index)
        available = {
            key(cell.sheet_name, cell.address): cell
            for cell in candidates
        }
        context = {
            "truncated": data_index.truncated,
            "max_changes": MAX_CHANGES,
            "supports": [
                "value",
                "clear",
                "explicit_formula",
                "cell_range",
                "multiple_sheets",
            ],
            "cells": [
                {
                    "sheet_name": cell.sheet_name,
                    "reference": cell.address,
                    "value": cell.formula or cell.value,
                    "formula": cell.formula,
                    "value_type": cell.value_type,
                }
                for cell in candidates
            ],
        }
        draft = await self._generator.generate(instruction, data_index.filename, context)
        changes, risks = validate_changes(
            draft.changes, available, data_index, instruction
        )
        limitations = list(draft.limitations)
        if data_index.truncated:
            limitations.append("대용량 워크북의 일부 셀은 변경 후보 검색에서 제외되었습니다.")
        if not draft.changes:
            limitations.append("지시에서 안전하게 특정할 변경 셀을 찾지 못했습니다.")
        if changes and risks:
            limitations.append(
                f"적용 가능한 {len(changes)}개 셀만 제안하고, 확인이 필요한 항목은 제외했습니다."
            )
        ready = bool(changes)
        summary = (
            f"승인 전 확인할 {len(changes)}개 셀 변경안을 준비했습니다."
            if ready
            else "안전하게 적용할 변경 셀을 확인하지 못했습니다."
        )
        return WritebackProposal(
            instruction=instruction,
            status=WritebackStatus.READY if ready else WritebackStatus.BLOCKED,
            summary=summary,
            changes=changes,
            risks=list(dict.fromkeys(risks)),
            limitations=list(dict.fromkeys(limitations)),
        )
