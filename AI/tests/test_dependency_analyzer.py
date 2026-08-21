from app.services.dependency_analyzer import analyze_dependencies
from app.services.formula_analyzer import FormulaAnalysis


def test_groups_formula_references_with_bfs() -> None:
    summary = analyze_dependencies(
        [
            (
                "원본",
                [
                    FormulaAnalysis("C1", "=A1+B1", ["A1", "B1"]),
                    FormulaAnalysis("D1", "=C1*2", ["C1"]),
                ],
            ),
            (
                "요약",
                [FormulaAnalysis("A1", "='원본'!D1", ["'원본'!D1"])],
            ),
        ]
    )

    assert summary.node_count == 5
    assert summary.formula_node_count == 3
    assert summary.edge_count == 4
    assert summary.cross_sheet_edge_count == 1
    assert summary.cluster_count == 1
    assert summary.cycle_count == 0
    assert summary.cyclic_node_count == 0
    assert summary.cycles == []

    cluster = summary.clusters[0]
    assert cluster.sheet_names == ["요약", "원본"]
    assert cluster.node_count == 5
    assert cluster.formula_count == 3
    assert any(
        edge.source == "원본!D1" and edge.target == "요약!A1"
        for edge in cluster.edges
    )


def test_tracks_named_and_external_references_without_expanding_them() -> None:
    summary = analyze_dependencies(
        [
            (
                "계산",
                [
                    FormulaAnalysis("A1", "=매출기준", ["매출기준"]),
                    FormulaAnalysis(
                        "A2",
                        "='[외부.xlsx]Sheet1'!A1",
                        ["'[외부.xlsx]Sheet1'!A1"],
                    ),
                ],
            )
        ]
    )

    assert summary.named_reference_count == 1
    assert summary.external_reference_count == 1
    assert summary.edge_count == 2


def test_detects_cross_sheet_formula_cycles() -> None:
    summary = analyze_dependencies(
        [
            (
                "입력",
                [FormulaAnalysis("A1", "='계산'!B1", ["'계산'!B1"])],
            ),
            (
                "계산",
                [
                    FormulaAnalysis("B1", "=C1", ["C1"]),
                    FormulaAnalysis("C1", "='입력'!A1", ["'입력'!A1"]),
                ],
            ),
        ]
    )

    assert summary.cycle_count == 1
    assert summary.cyclic_node_count == 3

    cycle = summary.cycles[0]
    assert cycle.node_count == 3
    assert cycle.edge_count == 3
    assert cycle.sheet_names == ["계산", "입력"]
    assert {node.id for node in cycle.nodes} == {
        "계산!B1",
        "계산!C1",
        "입력!A1",
    }
    assert {
        (edge.source, edge.target)
        for edge in cycle.edges
    } == {
        ("계산!B1", "입력!A1"),
        ("계산!C1", "계산!B1"),
        ("입력!A1", "계산!C1"),
    }


def test_detects_direct_self_reference_as_cycle() -> None:
    summary = analyze_dependencies(
        [("계산", [FormulaAnalysis("A1", "=A1+1", ["A1"])])]
    )

    assert summary.cycle_count == 1
    assert summary.cyclic_node_count == 1
    assert summary.cycles[0].nodes[0].id == "계산!A1"
    assert summary.cycles[0].edges[0].source == "계산!A1"
    assert summary.cycles[0].edges[0].target == "계산!A1"


def test_detects_self_reference_inside_a_range() -> None:
    summary = analyze_dependencies(
        [("계산", [FormulaAnalysis("A1", "=SUM(A1:B1)", ["A1:B1"])])]
    )

    assert summary.cycle_count == 1
    assert summary.cyclic_node_count == 1
    assert summary.cycles[0].edges[0].reference == "A1:B1"
