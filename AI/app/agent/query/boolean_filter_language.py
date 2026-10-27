"""Independently parse bounded AND/OR/NOT grammar; never infer tree shape from a model."""
from dataclasses import dataclass
import re

from app.agent.query.boolean_filter_lexing import CONNECTOR, NEGATION, leaf_at, spaces
from app.agent.query.boolean_filter_models import BooleanFilterExpression as Node
from app.agent.query.tabular_request_literals import source_headers, without_literals


def boolean_question(question):
    text = without_literals(question)
    text = re.sub(r"\b(?:is|are)\s+not\b|\bnot\s+equal\s+to\b", " ", text, flags=re.I)
    return bool(re.search(r"\b(?:OR|NOT|either)\b|또는|혹은|이거나|\|\||"
                          r"\([^)]*(?:=|!=|이상|이하|아닌|제외)[^)]*\)", text, re.I))


@dataclass
class ParsedBoolean:
    expression: Node
    filters: list
    remainder: str


class Parser:
    def __init__(self, text, table, position):
        self.text, self.table, self.position = text, table, position
        self.filters, self.inherited = [], None

    def parse(self, minimum=0, depth=0):
        if depth > 5 or len(self.filters) >= 8:
            raise ValueError("Boolean condition exceeds safe bounds")
        self.position = spaces(self.text, self.position)
        negation = NEGATION.match(self.text, self.position)
        if negation:
            self.position = negation.end()
            node = Node(operator="not", children=[self.parse(3, depth + 1)])
        elif self.text[self.position:self.position + 1] == "(":
            self.position += 1
            node = self.parse(0, depth + 1)
            self.position = spaces(self.text, self.position)
            if self.text[self.position:self.position + 1] != ")":
                raise ValueError("Unmatched parenthesis")
            self.position += 1
            exclude = re.match(r"\s*(?:[이가]\s*)?(?:제외|아닌)(?![가-힣])", self.text[self.position:])
            if exclude:
                self.position += exclude.end()
                node = Node(operator="not", children=[node])
        else:
            result = leaf_at(self.text, self.position, self.table, self.inherited)
            if result is None:
                raise ValueError("A boolean condition must bind an exact source field and literal")
            condition, self.position, self.inherited, _ = result
            node = Node(operator="predicate", filter_index=len(self.filters))
            self.filters.append(condition)
        while connector := CONNECTOR.match(self.text, self.position):
            op = "or" if connector[1].casefold() in {"or", "또는", "혹은", "이거나", "거나", "||"} else "and"
            precedence = 1 if op == "or" else 2
            if precedence < minimum:
                break
            self.position = connector.end()
            right = self.parse(precedence + 1, depth + 1)
            children = list(node.children) if node.operator == op else [node]
            children += list(right.children) if right.operator == op else [right]
            node = Node(operator=op, children=children)
        return node


def parse_boolean(question, table):
    # A single contiguous condition expression may be preceded/followed by
    # output instructions; unsupported residue is checked separately.
    masked = without_literals(question)
    headers = source_headers(question, table)
    starts = {match.start() for match in re.finditer(r"\(|\bNOT\b|아닌\s*조건|제외\s*조건", masked, re.I)
              if not any(header.start() <= match.start() < header.end() for _, header in headers)}
    starts |= {position for position in range(len(question))
               if (position == 0 or not question[position - 1].isalnum()) and leaf_at(question, position, table)}
    if not starts:
        return None
    start = min(starts)
    parser = Parser(question, table, start)
    try:
        expression = parser.parse()
        end = parser.position
        remainder = question[:start] + " " * (end - start) + question[end:]
        grammar = remainder
        for _, header in reversed(sorted(headers, key=lambda item: item[1].start())):
            grammar = grammar[:header.start()] + " " * (header.end() - header.start()) + grammar[header.end():]
        if boolean_question(grammar) or re.search(r"[()]", without_literals(grammar)):
            return None
        return ParsedBoolean(expression, parser.filters, remainder)
    except (ValueError, IndexError, RecursionError):
        return None


def expression_key(expression, filters):
    if expression is None:
        parts = [leaf_key(item) for item in filters]
        return combine("and", parts)
    if expression.operator == "predicate":
        return leaf_key(filters[expression.filter_index])
    parts = [expression_key(child, filters) for child in expression.children]
    return combine(expression.operator, parts)


def leaf_key(condition):
    op = condition.operator
    value = condition.value.casefold() if isinstance(condition.value, str) else condition.value
    base = ("leaf", condition.column_id, "equals" if op == "not_equals" else "is_blank" if op == "not_blank" else op,
            type(value).__name__, value, condition.value_unit)
    return ("not", base) if op in {"not_equals", "not_blank"} else base


def combine(operator, parts):
    if operator == "not":
        return parts[0][1] if parts[0][0] == "not" else ("not", parts[0])
    flattened = [child for part in parts for child in (part[1:] if part[0] == operator else [part])]
    return flattened[0] if len(flattened) == 1 else (operator, *sorted(flattened, key=repr))
