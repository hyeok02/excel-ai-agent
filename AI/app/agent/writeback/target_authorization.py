"""An explicit address authorizes only its destination, not nearby context."""
import re

from app.agent.writeback.references import expand_reference, key
from app.agent.writeback.target_semantics import semantic_target_risk
from app.agent.writeback.target_syntax import sheet_mentions, target_mentions
from app.agent.tools.workbook_header_index import detect_header_rows


class TargetAuthorization:
    def __init__(self, instruction, index):
        self.instruction, self.index = instruction, index
        sheets = {row.sheet_name for row in index.rows}
        self.masked, mentions = target_mentions(instruction, sheets)
        self.all_mentions = mentions
        self.mentions = [item for item in mentions if item.destination]
        self.excluded = [item for item in mentions if not item.destination]
        self.headers = None
        self.cells = {key(cell.sheet_name, cell.address): cell
                      for row in index.rows for cell in row.cells}
        self.targets = {}
        self.unresolved = False
        for position, mention in enumerate(self.mentions):
            refs = expand_reference(mention.reference)
            matching = {cell.sheet_name for cell in self.cells.values() if cell.address in refs}
            sheet = mention.sheet or (next(iter(matching)) if len(matching) == 1 else None)
            if sheet is None:
                self.unresolved = True
                continue
            local = self._local_instruction(position)
            for ref in refs:
                self.targets.setdefault(key(sheet, ref), []).append(local)

    def _local_instruction(self, position):
        mention = self.mentions[position]
        end = min((item.start for item in self.all_mentions if item.start > mention.start),
                  default=len(self.instruction))
        local = self.instruction[mention.end:end]
        linking = local
        for low, high, _ in reversed(sheet_mentions(local, {row.sheet_name for row in self.index.rows})):
            linking = linking[:low] + linking[high:]
        # "B2와 C2를 12로" shares one operation; "B2를 12로, C2를 15로" does not.
        if re.fullmatch(r"[\s,、&!]*(?:(?:와|과|및|그리고|and)[\s,!]*)?", linking, re.I):
            return self._local_instruction(position + 1) if position + 1 < len(self.mentions) else local
        if not local.strip() and position == 0:
            return self.instruction[:mention.start]
        return local

    def instruction_for(self, cell):
        if any(cell.address in expand_reference(item.reference)
               and (item.sheet is None or item.sheet.casefold() == cell.sheet_name.casefold())
               for item in self.excluded):
            return "", "참고하거나 변경에서 제외한 셀은 수정 대상으로 사용할 수 없습니다."
        if not self.mentions:
            if self.headers is None:
                self.headers = detect_header_rows(self.index.rows)
            return self.instruction, semantic_target_risk(cell, self.instruction, self.index, self.headers)
        instructions = self.targets.get(key(cell.sheet_name, cell.address), [])
        if not instructions:
            return "", "요청에 명시한 변경 대상 시트·셀·범위와 일치하지 않습니다."
        if len(set(instructions)) > 1:
            return "", "같은 셀에 여러 변경 지시가 있어 적용할 값을 확정하지 못했습니다."
        return instructions[0], None

    def missing_risks(self, changes):
        proposed = {key(change.sheet_name, change.reference) for change in changes}
        missing = [target for target in self.targets if target not in proposed]
        risks = []
        if missing:
            risks.append("명시한 변경 대상 중 변경안에서 확인하지 못한 셀: " + ", ".join(missing[:12]))
        if self.unresolved:
            risks.append("여러 시트에 같은 주소가 있어 일부 변경 대상 시트를 확정하지 못했습니다.")
        return risks
