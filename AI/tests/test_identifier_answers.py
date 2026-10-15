from app.agent.query.identifier_answers import missing_identifier_answer
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.query.models import QuestionAnswerStatus


def _index() -> WorkbookDataIndex:
    row = IndexedRow(
        "장비", 2, (IndexedCell("장비", "A2", "CVD #1", None),)
    )
    return WorkbookDataIndex("cvd.xlsx", (row,), 1, False)


def test_missing_hash_identifier_gets_a_specific_answer() -> None:
    answer = missing_identifier_answer("CVD #99의 IP는?", _index())

    assert answer is not None
    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    assert "#99 항목을 찾지 못했습니다" in answer.answer


def test_existing_hash_identifier_continues_to_normal_lookup() -> None:
    assert missing_identifier_answer("CVD #1의 IP는?", _index()) is None


def test_hash_rank_is_not_blocked_without_a_hash_identifier_system() -> None:
    row = IndexedRow(
        "주주", 2, (IndexedCell("주주", "A2", 1, None),)
    )
    index = WorkbookDataIndex("owners.xlsx", (row,), 1, False)

    assert missing_identifier_answer("#1 주주는?", index) is None


def test_unrelated_hash_family_does_not_block_a_plain_order_number() -> None:
    rows = (
        IndexedRow("주문", 2, (IndexedCell("주문", "A2", "Order 123", None),)),
        IndexedRow("장비", 2, (IndexedCell("장비", "A2", "CVD #1", None),)),
    )
    index = WorkbookDataIndex("mixed.xlsx", rows, 2, False)

    assert missing_identifier_answer("Order #123은?", index) is None


def test_truncated_index_never_declares_an_identifier_missing() -> None:
    index = WorkbookDataIndex("cvd.xlsx", _index().rows, 100, True)

    assert missing_identifier_answer("CVD #99의 IP는?", index) is None
