"""Rows whose newer value is above their older one, counted only when nothing else answered."""
from types import SimpleNamespace

from app.agent.query import column_change_counts as module
from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow, QueryTable
from tests.test_named_series_answers import Names

GROUPS = {"Northeast", "U.S. Total"}
ROWS = [("Northeast", 30, 29, 20, 21), ("Maine", 32, 28, 21, 21.5), ("Vermont", 23, 22, 19, 18),
        ("Ohio", 19, 20, 12, 11), ("U.S. Total", 18, 17, 14, 13)]


class Kinds:
    async def classify(self, question, header, labels):
        return SimpleNamespace(status="selected", kind="주", candidate_ids=[i for i, name in enumerate(labels) if name not in GROUPS])


def _table():
    def column(letter, header, parent=None):
        return QueryColumn(id=letter, header=header, header_reference=f"P!{letter}4", sample_values=(),
                           header_path=((f"P!{letter}3", parent),) if parent else ())
    columns = (column("A", "State"), column("B", "August 2026", "Residential"), column("C", "August 2025", "Residential"),
               column("D", "August 2026", "Commercial"), column("E", "August 2025", "Commercial"))
    rows = tuple(QueryRow(row_number=number, values=dict(zip("ABCDE", values))) for number, values in enumerate(ROWS, 5))
    return QueryTable(id="P!A4:E9", sheet_name="P", reference="A4:E9", columns=columns, rows=rows, complete=True)


def _ask(monkeypatch, question, names=None):
    monkeypatch.setattr(module, "build_query_tables", lambda summary: [_table()])
    return module.column_change_count_answer(question, object(), SimpleNamespace(rows=()),
                                             Names(names or {"상업용": "Commercial"}), Kinds())


def test_the_named_group_rows_of_the_asked_kind_are_compared_and_counted(monkeypatch):
    answer = _ask(monkeypatch, "상업용 전기요금이 작년보다 오른 주는 몇 개야?")
    assert answer.answer == "Commercial 기준 August 2026 값이 August 2025보다 높은 주: 2개 (비교한 3개 중)\nVermont, Ohio"
    assert "Northeast" in answer.limitations[1] and answer.status == "limited"
    down = _ask(monkeypatch, "가정용 요금이 작년보다 내린 주는 몇 개야?", {"가정용": "Residential"})
    assert down.answer.endswith("낮은 주: 1개 (비교한 3개 중)\nOhio")


def test_no_named_group_no_count_or_no_comparison_answers_nothing(monkeypatch):
    assert _ask(monkeypatch, "요금이 작년보다 오른 주는 몇 개야?", {}) is None
    assert _ask(monkeypatch, "상업용 전기요금이 작년보다 오른 주는?") is None
    assert _ask(monkeypatch, "상업용 전기요금은 몇 개야?") is None
