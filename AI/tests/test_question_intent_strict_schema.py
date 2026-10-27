"""Local SDK conversion only: no model invocation or remote schema request."""
from openai.lib._pydantic import to_strict_json_schema
import pytest

from app.agent.query.intent_models import QuestionIntentDraft
from tests.support.offline_network import install_network_guard


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    install_network_guard(monkeypatch)


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def test_strict_response_schema_has_closed_objects_and_every_property_required():
    schema = to_strict_json_schema(QuestionIntentDraft)
    objects = [node for node in nodes(schema) if node.get("type") == "object"]
    assert len(objects) >= 10
    for node in objects:
        assert node.get("additionalProperties") is False, node
        assert set(node.get("properties", {})) == set(node.get("required", [])), node


def test_recursive_boolean_definition_and_composite_plan_refs_remain_resolvable():
    schema = to_strict_json_schema(QuestionIntentDraft)
    definitions = schema["$defs"]
    assert {"BooleanFilterExpression", "CompositeQueryPlan", "CompositeQuestionPart",
            "TabularQueryPlan"} <= definitions.keys()
    expression = definitions["BooleanFilterExpression"]
    assert expression["properties"]["children"]["items"] == {
        "$ref": "#/$defs/BooleanFilterExpression"}
    for node in nodes(schema):
        reference = node.get("$ref")
        if reference is not None:
            assert reference.startswith("#/$defs/"), reference
            assert reference.rsplit("/", 1)[-1] in definitions, reference


def test_composite_schema_is_bounded_and_cannot_recursively_add_subquestions():
    schema = to_strict_json_schema(QuestionIntentDraft)
    composite = schema["$defs"]["CompositeQueryPlan"]["properties"]["parts"]
    assert composite["minItems"] == 2 and composite["maxItems"] == 4
    assert "composite_query" not in schema["$defs"]["CompositeQuestionPart"]["properties"]
