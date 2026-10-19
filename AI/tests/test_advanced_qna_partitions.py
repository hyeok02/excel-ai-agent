"""Each group has its own bounded ranking over the complete original source."""
from dataclasses import replace

import pytest

from tests.support.advanced_qna_fixtures import checked, partition_plan, records, source
from tests.support.large_workbook_fixtures import ask, equal, fresh_index, offline, tiny_caps


@pytest.mark.parametrize("provider", [False, True])
def test_each_group_top_n_is_not_a_global_top_n(provider):
    summary, index, _ = source()
    if not provider:
        index = replace(index, source_provider=None)
    answer = ask("Records 시트 각 Department별 Amount 상위 2개 Record와 Amount 보여줘", summary, index,
                 partition_plan(summary))
    checked(answer, scan=False)
    for label in ("Aone", "Atwo", "Bthree", "Bone", "Cone"):
        assert label in answer.answer, answer.model_dump()
    for label in ("Athree", "Afour", "Btwo"):
        assert label not in answer.answer, answer.model_dump()


def test_each_group_bottom_n_does_not_reuse_descending_selection(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 각 Department별 Amount 하위 1개 Record와 Amount 보여줘", summary, index,
                 partition_plan(summary, descending=False, per_group_limit=1))
    checked(answer, scan=True)
    assert all(label in answer.answer for label in ("Afour", "Btwo", "Cone"))
    assert all(label not in answer.answer for label in ("Aone", "Atwo", "Bthree", "Bone"))


def test_filter_applies_before_every_partition_ranking(tiny_caps):
    summary, index, _ = source()
    answer = ask("Records 시트 State가 active인 각 Department별 Amount 상위 2개 Record와 Amount 보여줘",
                 summary, index, partition_plan(summary, filters=[equal("E", "active")]))
    checked(answer, scan=True)
    assert "Bone" in answer.answer and "Btwo" in answer.answer
    assert "Bthree" not in answer.answer


def test_partition_boundary_tie_is_explicit_and_exact_n_is_preserved(tiny_caps):
    matrix = records()
    matrix[-1][1] = 40
    summary, index, _ = source(matrix)
    answer = ask("Records 시트 각 Department별 Amount 상위 1개 Record와 Amount 보여줘", summary, index,
                 partition_plan(summary, per_group_limit=1))
    checked(answer, scan=True)
    assert "Aone" in answer.answer and "Afour" not in answer.answer
    assert any("동점" in limitation for limitation in answer.limitations), answer.model_dump()


@pytest.fixture(scope="module")
def large_partition_population():
    matrix = [["Record", "Amount", "Department", "Customer"]]
    matrix.extend([f"Row{number}", number, "Alpha", f"Client{number % 7}"]
                  for number in range(1, 10_002))
    matrix.extend([["BetaWinner", 42, "Beta", "Client8"], ["TailWinner", 99_999, "Alpha", "Client9"]])
    return source(matrix)


def test_real_large_table_includes_tail_winner_and_tail_group(large_partition_population):
    summary, _, content = large_partition_population
    index = fresh_index(summary, content)
    assert index.truncated_for({"Records"})
    answer = ask("Records 시트 각 Department별 Amount 상위 1개 Record와 Amount 보여줘", summary, index,
                 partition_plan(summary, per_group_limit=1))
    checked(answer, scan=True)
    assert "TailWinner" in answer.answer and "BetaWinner" in answer.answer
    assert "Row10001" not in answer.answer
