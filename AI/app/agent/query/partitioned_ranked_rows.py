"""Keep a bounded top-N heap for every source-defined group, not one global top-N."""
from dataclasses import replace

from app.agent.query.grouped_tabular_state import typed_key
from app.agent.query.partition_rank_identity import PartitionIdentities
from app.agent.query.streaming_ranked_rows import RankedRows
from app.agent.query.tabular_feature_contract import feature_contract_matches

MAX_PARTITIONS = 1000
MAX_RETAINED_ROWS = 10000
MAX_RETAINED_CHARACTERS = 2_000_000
MAX_PARTITION_CHARACTERS = 512000
MAX_DISPLAY_ROWS = 500


class PartitionedRankedRows:
    def __init__(self, plan, table):
        self.plan = plan
        self.columns = {column.id: column for column in table.columns}
        self.groups = {}
        self.identities = PartitionIdentities(plan.identity_column_ids)
        self.count = self.population = self.hidden = 0
        self.retained_rows = self.characters = self.key_characters = 0
        self.valid = feature_contract_matches(plan, table)

    def add(self, row):
        if not self.valid:
            return False
        self.valid = self._add(row)
        return self.valid

    def _add(self, row):
        parts = []
        for column in self.plan.group_by:
            if column not in row.values or row.values[column] is None and row.formulas.get(column):
                return False
            part = typed_key(row.values[column], row.number_formats.get(column, "General"))
            if part is None:
                return False
            parts.append(part)
        identity = tuple(part[0] for part in parts)
        if not self.identities.add(identity, row):
            return False
        if identity not in self.groups:
            size = sum(len(part[1]) for part in parts)
            if len(self.groups) >= MAX_PARTITIONS or self.key_characters + size > MAX_PARTITION_CHARACTERS:
                return False
            self.key_characters += size
            ranked_plan = self.plan.model_copy(update={"group_by": [], "per_group_limit": None,
                                                       "limit": self.plan.per_group_limit})
            selected = list(dict.fromkeys(self.plan.column_ids))
            self.groups[identity] = ([part[1] for part in parts],
                                     RankedRows(ranked_plan, [self.columns[key] for key in selected]))
        _, ranked = self.groups[identity]
        before_rows, before_chars = len(ranked.heap), ranked.characters
        needed = set(self.plan.column_ids + self.plan.group_by + self.plan.identity_column_ids)
        needed.add(self.plan.order_by)
        if not needed <= row.values.keys() or any(row.formulas.get(key) and row.values[key] is None for key in needed):
            return False
        projected = replace(row, values={key: row.values[key] for key in needed},
                            number_formats={key: value for key, value in row.number_formats.items() if key in needed},
                            formulas={key: value for key, value in row.formulas.items() if key in needed})
        if not ranked.add(projected):
            return False
        self.retained_rows += len(ranked.heap) - before_rows
        self.characters += ranked.characters - before_chars
        if self.retained_rows > MAX_RETAINED_ROWS or self.characters > MAX_RETAINED_CHARACTERS:
            return False
        self.count += 1
        return True

    def render(self):
        if not self.valid:
            return None, []
        if not self.count:
            return "지정한 조건에 맞는 행이 없어 그룹별 순위를 계산할 행이 없습니다.", []
        desired = sum(min(ranked.count, self.plan.per_group_limit) for _, ranked in self.groups.values())
        lines = [f"조건에 맞는 전체 {self.count}개 행을 {len(self.groups)}개 그룹 안에서 각각 정렬했습니다.",
                 "동점은 각 그룹의 원본 행 순서로 선택합니다."]
        if self.plan.identity_column_ids:
            names = ", ".join(self.columns[key].header for key in self.plan.identity_column_ids)
            lines.append(f"‘{names}’ 조합은 각 그룹에서 빈 값 없이 한 행씩만 존재함을 확인했습니다.")
        shown = displayed_groups = tied_groups = 0
        for labels, ranked in self.groups.values():
            size = min(ranked.count, self.plan.per_group_limit)
            if shown + size > MAX_DISPLAY_ROWS:
                break
            text, _ = ranked.render()
            if text is None:
                return None, []
            label = "; ".join(f"{self.columns[key].header}: {value}"
                              for key, value in zip(self.plan.group_by, labels))
            lines.extend([label, text])
            tied_groups += ranked.boundary_tied()
            shown += size
            displayed_groups += 1
        limitations = []
        if tied_groups:
            limitations.append(f"표시한 {tied_groups}개 그룹의 순위 경계에 동점이 있어, "
                               f"원본 행 순서로 각 그룹에서 {self.plan.per_group_limit}개 행만 선택했습니다.")
        if shown < desired:
            limitations.append(f"전체 그룹별 순위 {desired}개 행 중 {displayed_groups}개 그룹의 "
                               f"{shown}개 행만 표시했습니다(표시 한도 {MAX_DISPLAY_ROWS}행).")
        return "\n".join(lines), limitations
