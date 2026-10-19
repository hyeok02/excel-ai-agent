"""Bounded, typed grouping state over original rows, never a sampled population."""
import json

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.streaming_tabular_numeric import NumericAccumulator
from app.agent.query.tabular_filters import finite_number
from app.agent.query.tabular_numeric import _unit_identity
from app.agent.query.tabular_results import _display_cell
from app.agent.query.formula_resolution_values import EXCEL_ERRORS
from app.agent.query.grouped_aggregate_validation import valid_aggregate_plan
from app.agent.query.grouped_distinct_state import DistinctState

MAX_GROUPS = 1000
MAX_AGGREGATES = 12000
MAX_KEY_CHARACTERS = 512000


def typed_key(value, style):
    if value in (None, ""):
        return ("blank",), "빈칸 (누락)"
    if isinstance(value, bool):
        return ("boolean", value), f"{value} (논리값)"
    if finite_number(value):
        spec = parse_number_format(style)
        if spec.mode == "raw" and style.casefold().strip() != "general":
            return None
        label = _display_cell(value, style)
        # Raw value prevents rounded display formats from conflating distinct keys.
        label += f" (숫자; 원본값 {value})"
        return ("number", value, _unit_identity(spec)), label
    if isinstance(value, str):
        if value.strip().upper() in EXCEL_ERRORS:
            return None
        return ("text", value), f"{json.dumps(value, ensure_ascii=False)} (문자)"
    return None


class GroupState:
    def __init__(self, labels, measures):
        self.labels = labels
        self.count = 0
        self.numeric = {key: NumericAccumulator() for key in measures}
        self.distinct = set()
        self.skipped = 0


class GroupedState:
    def __init__(self, plan, table):
        self.plan = plan
        self.columns = {column.id: column for column in table.columns}
        self.measures = list(dict.fromkeys(plan.column_ids)) if plan.operation == "numeric_summary" else []
        self.groups = {}
        self.units = {key: NumericAccumulator() for key in self.measures}
        self.key_characters = 0
        self.distinct = DistinctState(plan.column_ids) if plan.operation == "distinct_count" else None
        self.valid = valid_aggregate_plan(plan, self.columns, self.measures)
        if self.valid and not plan.group_by:
            self.groups[()] = GroupState([], self.measures)

    def add(self, row):
        if not self.valid:
            return False
        if not self._add(row):
            self.valid = False
        return self.valid

    def _add(self, row):
        parts = []
        for key in self.plan.group_by:
            value = row.values.get(key)
            if value is None and row.formulas.get(key):
                return False
            part = typed_key(value, row.number_formats.get(key, "General"))
            if part is None:
                return False
            parts.append(part)
        identity = tuple(key for key, _ in parts)
        if identity not in self.groups:
            characters = sum(len(label) for _, label in parts)
            if (len(self.groups) >= MAX_GROUPS
                    or (len(self.groups) + 1) * max(1, len(self.measures)) > MAX_AGGREGATES
                    or self.key_characters + characters > MAX_KEY_CHARACTERS):
                return False
            self.key_characters += characters
            self.groups[identity] = GroupState([label for _, label in parts], self.measures)
        group = self.groups[identity]
        if self.distinct is not None and not self.distinct.add(group, row, typed_key):
            return False
        for key in self.measures:
            value, style = row.values.get(key), row.number_formats.get(key, "General")
            if value is None and row.formulas.get(key):
                return False
            # Global unit check also covers groups not retained in the final top N.
            if not self.units[key].add(value, style) or not group.numeric[key].add(value, style):
                return False
        group.count += 1
        return True
