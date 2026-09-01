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
        available = {
            key(cell.sheet_name, cell.address): cell
            for row in data_index.rows
            for cell in row.cells
        }
        candidates = select_writeback_candidates(instruction, data_index)
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
        return WritebackProposal(
            instruction=instruction,
            status=WritebackStatus.READY if ready else WritebackStatus.BLOCKED,
            summary=draft.summary,
            changes=changes,
            risks=list(dict.fromkeys(risks)),
            limitations=list(dict.fromkeys(limitations)),
        )
