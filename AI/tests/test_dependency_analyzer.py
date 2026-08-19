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
