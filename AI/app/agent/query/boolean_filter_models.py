"""Bounded boolean structure over a plan's existing, source-bound predicates."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BooleanFilterExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operator: Literal["predicate", "and", "or", "not"]
    filter_index: int | None = Field(default=None, ge=0, le=7)
    children: list["BooleanFilterExpression"] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def valid_node(self):
        if self.operator == "predicate":
            valid = self.filter_index is not None and not self.children
        else:
            valid = self.filter_index is None and (
                len(self.children) == 1 if self.operator == "not" else len(self.children) >= 2)
        if not valid:
            raise ValueError("Boolean nodes require a predicate index, one NOT child, or at least two AND/OR children")
        return self


def validate_expression(expression, count):
    if expression is None:
        return
    indices, nodes = [], []

    def visit(node, depth):
        if depth > 5 or len(nodes) >= 24:
            raise ValueError("Boolean expressions are limited to depth 5 and 24 nodes")
        nodes.append(node)
        if node.operator == "predicate":
            indices.append(node.filter_index)
        for child in node.children:
            visit(child, depth + 1)

    visit(expression, 1)
    if sorted(indices) != list(range(count)):
        raise ValueError("Every filter must occur exactly once in the boolean expression")
