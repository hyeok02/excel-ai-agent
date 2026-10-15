"""Header co-location is a source fact, not proof of identical real-world work."""
import pytest

from app.agent.query.header_relation_answers import header_relation_answer
from app.agent.query.header_relation_models import HeaderRelationPlan
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from tests.tabular_query_fixtures import table_fixture


def _answer(summary, index, question, mentions, columns=None, **plan_values):
    table = build_query_tables(summary)[0]
    plan = HeaderRelationPlan(
        table_id=plan_values.pop("table_id", table.id),
        column_ids=columns or [table.columns[1].id], mentions=mentions, **plan_values,
    )
    intent = QuestionIntent(False, "field_relation", header_relation=plan)
    return header_relation_answer(question, summary, index, intent)


@pytest.mark.parametrize("header,question,mentions", [
    ("Orion, Vega 작업", "Orion과 Vega 작업이 같은 거야?", ["Orion", "Vega 작업"]),
    ("TCK,성수계전 작업", "TCK와 성수계전 작업이 똑같은거야?", ["TCK", "성수계전 작업"]),
    ("한빛·새봄 점검", "한빛과 새봄 점검이 같은 거야?", ["한빛", "새봄 점검"]),
    ("Atlas / Lyra 확인", "Atlas와 Lyra 확인은 동일한 항목이야?", ["Atlas", "Lyra 확인"]),
    ("North & South inspection", "Are North and South inspection the same?", ["North", "South inspection"]),
    ("Orion\nVega 작업", "Orion과 Vega 작업이 같은 거야?", ["Orion", "Vega 작업"]),
])
def test_joint_source_header_is_explained_without_claiming_semantic_equivalence(header, question, mentions):
    summary, index = table_fixture([(7, 4, [["Record", header], ["R1", "yes"], ["R2", "no"]])])
    result = _answer(summary, index, question, mentions)
    assert result is not None
    assert result.status == "limited", result.answer
    assert result.verification.level == "source_checked"
    assert "하나의 열" in result.answer
    assert all(mention in result.answer for mention in mentions)
    assert any(item.reference == "E7" and item.value == header for item in result.evidence)
    assert any(word in result.answer + " ".join(result.limitations)
               for word in ("단정", "확인할 수 없", "확정할 수 없"))
    assert "같은 작업입니다" not in result.answer


def test_separate_source_headers_explain_separate_fields_not_different_business_meanings():
    summary, index = table_fixture([(3, 2, [
        ["Record", "Orion 작업", "Vega 작업"], ["R1", "yes", "yes"], ["R2", "no", "no"],
    ])])
    result = _answer(summary, index, "Orion 작업과 Vega 작업이 같은 거야?",
                     ["Orion 작업", "Vega 작업"], columns=["C", "D"])
    assert result.status == "limited", result.answer
    assert result.verification.level == "source_checked"
    assert "서로 다른 열" in result.answer
    assert {"C3", "D3"} <= {item.reference for item in result.evidence}
    assert "서로 다른 작업입니다" not in result.answer
    assert any(word in result.answer + " ".join(result.limitations)
               for word in ("단정", "확인할 수 없", "확정할 수 없"))


@pytest.mark.parametrize("override", [
    {"column_ids": []}, {"column_ids": ["A", "B", "C"]},
    {"mentions": []}, {"mentions": ["Orion"]}, {"mentions": ["Orion", "Vega", "Lyra"]},
    {"sql": "SELECT arbitrary_data"},
])
def test_relation_plan_schema_rejects_unsupported_shapes(override):
    fields = {"table_id": "Arbitrary!A1:B3", "column_ids": ["B"], "mentions": ["Orion", "Vega"]}
    with pytest.raises(ValueError):
        HeaderRelationPlan(**{**fields, **override})


def test_no_plan_can_derive_safe_relation_from_whole_source_label_parts():
    summary, index = table_fixture([(1, 1, [["Record", "Orion, Vega 작업"], ["R1", "yes"]])])
    result = header_relation_answer("Orion과 Vega 작업이 같은 거야?", summary, index, QuestionIntent(False))
    assert result is not None
    assert result.status == "limited"
    assert result.verification.level == "source_checked"
    assert "하나의 열" in result.answer
    assert "같은 작업입니다" not in result.answer


def test_no_plan_preserves_unrelated_numeric_question_routes():
    summary, index = table_fixture([(1, 1, [["Record", "Orion, Vega 작업"], ["R1", 10]])])
    result = header_relation_answer("Orion과 Vega 작업의 합계는?", summary, index, QuestionIntent(False))
    assert result is None
