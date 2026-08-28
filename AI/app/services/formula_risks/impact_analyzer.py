from collections import defaultdict, deque
from dataclasses import replace

from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from app.services.dependencies.references import cell_id, reference_node
from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.models import FormulaRiskFinding, FormulaRiskImpact

KIND_WEIGHT = {
    "broken_reference": 32,
    "missing_sheet": 30,
    "external_reference": 22,
    "dynamic_function": 20,
    "formula_pattern_mismatch": 25,
    "hardcoded_value": 28,
}


def add_impact_analysis(
    findings: list[FormulaRiskFinding],
    formulas_by_sheet: list[tuple[str, list[FormulaAnalysis]]],
) -> list[FormulaRiskFinding]:
    graph = _ImpactGraph(formulas_by_sheet)
    return [replace(item, impact=_impact(item, graph)) for item in findings]


class _ImpactGraph:
    def __init__(self, formulas_by_sheet: list[tuple[str, list[FormulaAnalysis]]]):
        self.direct: dict[str, set[str]] = defaultdict(set)
        self.ranges: dict[str, list[tuple[int, int, int, int, str]]] = defaultdict(list)
        self.formula_nodes: set[str] = set()
        for sheet_name, formulas in formulas_by_sheet:
            for formula in formulas:
                target = cell_id(sheet_name, formula.cell)
                self.formula_nodes.add(target)
                for reference in formula.references:
                    self._add_reference(sheet_name, reference, target)

    def dependents(self, node: str) -> set[str]:
        dependents = set(self.direct.get(node, set()))
        sheet_name, address = node.rsplit("!", 1)
        if ":" in address:
            return dependents
        row, column = coordinate_to_tuple(address)
        for min_col, min_row, max_col, max_row, target in self.ranges[sheet_name]:
            if min_row <= row <= max_row and min_col <= column <= max_col:
                dependents.add(target)
        return dependents

    def _add_reference(self, current_sheet: str, raw: str, target: str) -> None:
        source = reference_node(current_sheet, raw)
        if source.kind == "range" and source.sheet and source.cell:
            bounds = range_boundaries(source.cell)
            self.ranges[source.sheet].append((*bounds, target))
        else:
            self.direct[source.id].add(target)


def _impact(finding: FormulaRiskFinding, graph: _ImpactGraph) -> FormulaRiskImpact:
    start = cell_id(finding.sheet_name, finding.cell)
    visited = {start}
    queue = deque([(start, 0)])
    affected: set[str] = set()
    max_depth = 0
    while queue:
        node, depth = queue.popleft()
        for dependent in graph.dependents(node):
            if dependent in visited:
                continue
            visited.add(dependent)
            affected.add(dependent)
            max_depth = max(max_depth, depth + 1)
            queue.append((dependent, depth + 1))
    sheets = sorted({node.rsplit("!", 1)[0] for node in affected})
    score = _risk_score(finding, len(affected), len(sheets), max_depth)
    return FormulaRiskImpact(
        affected_formula_count=len(affected),
        affected_sheet_count=len(sheets),
        affected_sheets=sheets,
        max_depth=max_depth,
        risk_score=score,
        risk_level=_risk_level(score),
    )


def _risk_score(
    finding: FormulaRiskFinding,
    affected_count: int,
    sheet_count: int,
    max_depth: int,
) -> int:
    severity = 35 if finding.severity == "error" else 18
    kind = KIND_WEIGHT.get(finding.kind, 15)
    impact = min(affected_count * 2, 20)
    spread = min(sheet_count * 5, 15)
    depth = min(max_depth * 3, 12)
    return min(severity + kind + impact + spread + depth, 100)


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"
