"""Render complete-source grouped statistics and stable aggregate rankings."""
from app.agent.query.grouped_tabular_state import GroupedState
from app.agent.query.grouped_aggregate_postprocess import AggregatePostprocess, aggregate_value

MAX_DISPLAY_GROUPS = 50


class GroupedAccumulator:
    def __init__(self, plan, table):
        self.plan = plan
        self.count = self.population = self.hidden = 0
        self.state = GroupedState(plan, table)

    def add(self, row):
        if not self.state.add(row):
            return False
        self.count += 1
        return True

    def render(self):
        if not self.state.valid:
            return None, []
        groups = list(self.state.groups.values())
        if not groups:
            return "지정한 조건에 맞는 행이 없어 집계할 그룹이 없습니다.", []
        original_count = len(groups)
        postprocess = AggregatePostprocess(self.state)
        groups = postprocess.select(groups)
        if groups is None:
            return None, []
        ranked = self.plan.order_by is not None or self.plan.limit is not None
        if ranked:
            if any(self._rank_value(group) is None for group in groups):
                return None, []
            # Stable sort: ties retain the first original-row occurrence order.
            groups.sort(key=self._rank_value, reverse=self.plan.descending)
        limit = self.plan.limit or MAX_DISPLAY_GROUPS
        visible, limitations = groups[:limit], self._limitations()
        if self.plan.limit is None and len(groups) > limit:
            limitations.append(f"총 {len(groups)}개 그룹 중 앞의 {limit}개 그룹만 표시했습니다.")
        if ranked and len(groups) > limit and self._rank_value(groups[limit - 1]) == self._rank_value(groups[limit]):
            limitations.append("순위 경계에 동점이 있어 원본에서 먼저 등장한 그룹을 우선 표시했습니다.")
        lines = [f"조건에 맞는 {self.count}개 행을 {original_count}개 그룹으로 집계했습니다."]
        if not self.plan.group_by:
            lines = [f"조건에 맞는 {self.count}개 행 전체를 집계했습니다."]
        if self.plan.having:
            lines.append(f"전체 집계 후 조건을 만족하는 그룹은 {len(groups)}개입니다.")
        if self.plan.share_of_total:
            lines.append("비중 분모는 행 조건 적용 후의 전체 집계이며, 집계 후 조건·순위·표시 개수로 줄이지 않았습니다.")
        if ranked:
            lines.append("전체 그룹 집계 결과로 정렬했으며 동점은 원본 첫 등장 순서입니다.")
        for group in visible:
            label = "; ".join(f"{self.state.columns[key].header}: {text}"
                              for key, text in zip(self.plan.group_by, group.labels))
            parts = [f"행 개수 {group.count}건"]
            if self.plan.operation == "distinct_count":
                targets = ", ".join(self.state.columns[key].header for key in self.plan.column_ids)
                parts.append(f"{targets}: 중복 제외 개수 {len(group.distinct)}건 (불완전한 값 제외 {group.skipped}개 행)")
            for key, accumulator in group.numeric.items():
                value = accumulator.render(self.plan.statistic)
                if value is None:
                    value = f"숫자 없음 (빈칸 {accumulator.blanks}건; 0으로 간주하지 않음)"
                parts.append(f"{self.state.columns[key].header}: {value}")
            share = postprocess.share_text(group)
            if share:
                parts.append(share)
            lines.append((label + " — " if label else "전체 — ") + "; ".join(parts))
        return "\n".join(lines), limitations

    def _rank_value(self, group):
        return aggregate_value(self.plan, group, self.plan.order_by)

    def _limitations(self):
        skipped = sum(group.skipped for group in self.state.groups.values())
        if skipped:
            return [f"중복 제외 집계에서 빈칸·공백 또는 구성 항목이 빠진 {skipped}개 행을 제외했습니다."]
        return []
