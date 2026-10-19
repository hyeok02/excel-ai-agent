"""Stable, numeric top/bottom rows with bounded retained source observations."""
from decimal import Decimal
import heapq

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.tabular_filters import finite_number
from app.agent.query.tabular_numeric import _unit_identity
from app.agent.query.tabular_results import _display_cell

MAX_RANKED_CHARACTERS = 2_000_000


class RankedRows:
    def __init__(self, plan, columns):
        self.plan, self.columns = plan, columns
        self.count = self.population = self.hidden = self.characters = 0
        self.capacity = (plan.limit or 50) + 1
        self.heap, self.styles = [], {}
        self.unit = None

    def add(self, row):
        value = row.values.get(self.plan.order_by)
        if not finite_number(value):
            return False
        style = row.number_formats.get(self.plan.order_by, "General")
        if style not in self.styles:
            if len(self.styles) >= 256:
                return False
            self.styles[style] = parse_number_format(style)
        spec = self.styles[style]
        if spec.mode == "raw" and style.casefold().strip() != "general":
            return False
        unit = _unit_identity(spec)
        if self.unit is not None and self.unit != unit:
            return False
        self.unit = unit
        self.count += 1
        number = Decimal(str(value))
        quality = number if self.plan.descending else number.copy_negate()
        size = sum(len(str(value)) for value in row.values.values())
        entry = (quality, -self.count, row, size)
        if len(self.heap) < self.capacity:
            heapq.heappush(self.heap, entry)
            self.characters += size
        elif entry[:2] > self.heap[0][:2]:
            removed = heapq.heapreplace(self.heap, entry)
            self.characters += size - removed[3]
        return self.characters <= MAX_RANKED_CHARACTERS

    def render(self):
        if not self.count:
            return "지정한 조건에 맞는 행이 없습니다.", []
        entries = sorted(self.heap, key=lambda entry: entry[:2], reverse=True)
        limit = self.plan.limit or 50
        lines = []
        for _, _, row, _ in entries[:limit]:
            parts = []
            for column in self.columns:
                value = row.values[column.id]
                if value is None and row.formulas.get(column.id):
                    return None, []
                rendered = _display_cell(value, row.number_formats.get(column.id, "General"))
                parts.append(f"{column.header}: {rendered}")
            lines.append("; ".join(parts))
        limitations = []
        if self.plan.limit is None and self.count > limit:
            limitations.append(f"조건에 맞는 {self.count}개 행을 모두 정렬한 결과 중 앞의 {limit}개 행만 표시했습니다.")
        if len(entries) > limit and entries[limit - 1][0] == entries[limit][0]:
            lines.append(f"경계값이 같은 행은 원본 행 순서로 선택하여 {limit}개 행만 표시했습니다.")
        return "\n".join(lines), limitations

    def boundary_tied(self):
        entries = sorted(self.heap, key=lambda entry: entry[:2], reverse=True)
        limit = self.plan.limit or 50
        return len(entries) > limit and entries[limit - 1][0] == entries[limit][0]
