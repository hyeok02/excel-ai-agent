"""Keep numeric populations separate by explicit units and total/detail roles."""
import re

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.metric_observation_units import _currency, _magnitude
from app.agent.query.metric_unit_settings import _unambiguous_control
from app.agent.query.models import QuestionAnswer
from app.agent.query.tabular_population_semantics import ROLE_HEADERS as _ROLES, uses_currency, row_population_role

_UNITS = {"currency": "currency", "통화": "currency", "magnitude": "magnitude",
          "금액 단위": "magnitude", "unit": "unit", "units": "unit", "단위": "unit"}


def numeric_population(plan):
    return plan.operation == "numeric_summary" or plan.operation == "row_list" and bool(plan.order_by)


def population_controls(plan, table):
    if not numeric_population(plan):
        return set()
    metrics = plan.column_ids if plan.operation == "numeric_summary" else [plan.order_by]
    money = any(uses_currency(column) for column in table.columns if column.id in metrics)
    return {column.id for column in table.columns if column.header.strip().casefold() in _UNITS.keys() | _ROLES
            and (money or _UNITS.get(column.header.strip().casefold()) != "currency")}


def unit_qualified_headers(plan, table, headers):
    controls = {column.id for column in table.columns if column.header.strip().casefold() in _UNITS}
    values = [str(item.value) for item in plan.filters
              if item.column_id in controls and item.operator == "equals" and item.value not in (None, "")]
    return [header + " (" + " ".join(values) + ")" for header in headers] if values else headers


class NumericPopulationContext:
    """Bounded metadata state, usable for indexed and complete streamed rows."""
    def __init__(self, plan, table):
        self.plan, self.table = plan, table
        self.active = numeric_population(plan)
        self.controls = {column.id: column for column in table.columns
                         if column.id in population_controls(plan, table)}
        self.metrics = plan.column_ids if plan.operation == "numeric_summary" else [plan.order_by]
        self.identities, self.labels = {}, {}
        self.error = "집계 대상의 통화·단위 또는 행 구분을 원본과 확정하지 못했습니다."

    def add(self, row):
        if not self.active:
            return True
        if all(row.values.get(key) in (None, "") for key in self.metrics):
            return True
        # Ranking/share compares groups against each other, so units must agree
        # globally; ordinary grouped summaries may retain separate currencies.
        group = () if self.plan.share_of_total or self.plan.order_by else tuple(
            (type(row.values.get(key)).__name__, str(row.values.get(key))) for key in self.plan.group_by)
        if len(self.identities) > 12000:
            return False
        units = {}
        role = row_population_role(row, self.table)
        if role is None:
            self.error = "행 구분은 상세로 표시됐지만 원본 라벨·수식은 합계·소계를 가리킵니다. 중복 집계하지 않도록 원본 행 구분을 확인해 주세요."
            return False
        for key, column in self.controls.items():
            header = column.header.strip().casefold()
            value = row.values.get(key)
            if row.formulas.get(key) and value is None:
                return False
            normalized = str(value or "").strip().casefold()
            if header in _ROLES:
                continue
            kind = _UNITS[header]
            parser = _currency if kind == "currency" else _magnitude if kind == "magnitude" else None
            parsed = _unambiguous_control(normalized, parser) if parser else normalized
            if not parsed and kind == "currency" and re.fullmatch(r"[a-z]{3}", normalized):
                parsed = normalized.upper()
            if not parsed and kind == "magnitude" and normalized in {"1", "ones", "units", "raw", "unscaled"}:
                parsed = "1"
            if not parsed or len(normalized) > 100 or re.search(r"[/,;]|\bor\b|또는", normalized):
                self.error = f"원본의 {column.header} 값이 누락되거나 모호합니다. 단위를 확인한 행 범위를 지정해 주세요."
                return False
            if kind in units and units[kind] != parsed:
                return False
            units[kind] = parsed
            self.labels.setdefault(column.header, set()).add(str(value).strip())
        for key in self.metrics:
            if row.values.get(key) in (None, ""):
                continue
            column = next(column for column in self.table.columns if column.id == key)
            metric_units = {kind: value for kind, value in units.items() if kind != "currency" or uses_currency(column)}
            identity = (*sorted(metric_units.items()), ("row_role", role))
            spec = parse_number_format(row.number_formats.get(key, "General"))
            for kind, parser in (("currency", _currency), ("magnitude", _magnitude)):
                expected = metric_units.get(kind)
                declared = [parser(column.header), parser(spec.prefix + spec.suffix)]
                if expected and any(value and value != expected and not (
                        kind == "currency" and value == "달러" and expected.endswith("달러")) for value in declared):
                    self.error = "항목명·셀 표시 형식과 행에 적힌 통화·단위가 충돌합니다. 원본 단위를 확인해 주세요."
                    return False
            token = group, key
            if token in self.identities and role == "total" and dict(self.identities[token]).get("row_role") == "total":
                self.error = "여러 합계·소계 행의 집계 범위가 겹치지 않는지 확인하지 못했습니다. 원본 그룹별로 구분하거나 한 집계 범위를 선택해 주세요."
                return False
            if token in self.identities and self.identities[token] != identity:
                if dict(self.identities[token]).get("row_role") != role:
                    self.error = "상세 행과 합계·소계 행이 섞여 중복 집계할 수 있습니다. 상세 행만 조건으로 지정하거나 범위를 구분해 주세요."
                else:
                    self.error = "통화·단위가 다른 값이 섞여 하나의 수치로 합산·비교하지 않았습니다. 통화·단위별로 집계하거나 조건을 지정해 주세요."
                return False
            self.identities[token] = identity
        return True

    def unavailable(self, question):
        return QuestionAnswer(question=question, answer=self.error, status="insufficient_evidence", confidence=0,
                              selected_tools=["tabular_query"], evidence=[], limitations=[self.error])

    def description(self):
        parts = [f"{header}: {', '.join(sorted(values))}" for header, values in self.labels.items()
                 if not any(column.header == header and column.id in self.plan.group_by
                            for column in self.controls.values())]
        return "원본 단위 기준 — " + "; ".join(parts) + ".\n" if parts else ""
