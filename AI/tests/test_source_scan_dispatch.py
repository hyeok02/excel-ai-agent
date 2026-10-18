import asyncio
import threading

from app.agent.query import service as service_module
from app.agent.query import tabular_source_alias_resolution as alias_module
from tests.support.large_workbook_fixtures import ask, offline, parsed, plan_for, tiny_caps, workbook


def test_service_scans_table_on_worker_thread(tiny_caps, monkeypatch):
    summary, index, _ = parsed(workbook({"Records": [
        ["Record", "Amount"], *[[f"Item{number}", number] for number in range(1, 9)],
    ]}))
    original = service_module.planned_tabular_answer
    calling_thread = threading.get_ident()
    observed = []

    def checked(*args):
        observed.append(threading.get_ident())
        return original(*args)

    monkeypatch.setattr(service_module, "planned_tabular_answer", checked)
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert "합계 36" in answer.answer
    assert observed and all(thread != calling_thread for thread in observed)


def test_alias_source_execution_does_not_block_event_loop(monkeypatch):
    calling_thread = threading.get_ident()
    sentinel = object()

    def checked(*args):
        assert threading.get_ident() != calling_thread
        return sentinel

    monkeypatch.setattr(alias_module, "source_label_alias_answer", checked)
    result = asyncio.run(alias_module.resolved_source_label_alias_answer("질문", None, None, None, None))
    assert result is sentinel


def test_row_count_context_anchors_do_not_add_unrequested_hidden_headers(tiny_caps):
    book = workbook({"Records": [["Record", "Hidden Measure", "Amount"],
                                 *[[f"Item{n}", n, n] for n in range(1, 9)]]})
    book.active.column_dimensions["B"].hidden = True
    summary, index, _ = parsed(book)
    plan = plan_for(summary, operation="row_count", columns=())
    answer = ask("Records 시트 전체 행 개수는?", summary, index, plan)
    assert answer.verification.level == "request_checked"
    anchors = {item.reference for item in answer.evidence if item.kind == "cell"}
    assert anchors == {"A1", "C1"}
