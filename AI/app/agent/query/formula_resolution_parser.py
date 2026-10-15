"""Parse a small Excel expression grammar without Python eval or execution."""
from dataclasses import dataclass

from openpyxl.formula.tokenizer import Tokenizer, TokenizerError

from app.agent.query.formula_resolution_models import FormulaLimits, FormulaUnavailable


@dataclass(frozen=True)
class FormulaNode:
    kind: str
    value: str
    args: tuple["FormulaNode", ...] = ()


_PRECEDENCE = {"=": 1, "<>": 1, "<": 1, ">": 1, "<=": 1, ">=": 1,
               "&": 2, "+": 3, "-": 3, "*": 4, "/": 4, "^": 5}


class FormulaParser:
    def __init__(self, formula: str, limits: FormulaLimits):
        if len(formula) > limits.max_formula_length:
            raise FormulaUnavailable("resource_limit")
        try:
            self.tokens = [t for t in Tokenizer(formula).items if t.type != "WHITE-SPACE"]
        except (TokenizerError, IndexError, ValueError):
            raise FormulaUnavailable("unsupported_expression") from None
        if len(self.tokens) > limits.max_tokens:
            raise FormulaUnavailable("resource_limit")
        self.position = 0
        self.limits = limits

    def parse(self) -> FormulaNode:
        result = self.expression(0, 0)
        if self.position != len(self.tokens):
            raise FormulaUnavailable("unsupported_expression")
        return result

    def expression(self, minimum: int, depth: int) -> FormulaNode:
        if depth > self.limits.max_depth:
            raise FormulaUnavailable("resource_limit")
        token = self.take()
        if token.type == "OPERAND":
            left = FormulaNode(token.subtype.lower(), token.value)
        elif token.type == "OPERATOR-PREFIX" and token.value in ("+", "-"):
            left = FormulaNode("unary", token.value, (self.expression(6, depth + 1),))
        elif token.type in ("PAREN", "FUNC") and token.subtype == "OPEN":
            left = self.group(token, depth + 1)
        else:
            raise FormulaUnavailable("unsupported_expression")
        while self.position < len(self.tokens):
            token = self.tokens[self.position]
            if token.type == "OPERATOR-POSTFIX" and token.value == "%":
                self.position += 1
                left = FormulaNode("unary", "%", (left,))
                continue
            precedence = _PRECEDENCE.get(token.value, -1)
            if token.type != "OPERATOR-INFIX" or precedence < minimum:
                break
            self.position += 1
            right = self.expression(precedence + 1, depth + 1)
            left = FormulaNode("binary", token.value, (left, right))
        return left

    def group(self, token, depth: int) -> FormulaNode:
        if token.type == "PAREN":
            result = self.expression(0, depth)
            self.close("PAREN")
            return result
        args = []
        if self.position < len(self.tokens) and self.tokens[self.position].subtype != "CLOSE":
            while True:
                args.append(self.expression(0, depth))
                if (self.position < len(self.tokens)
                        and self.tokens[self.position].type == "SEP"
                        and self.tokens[self.position].subtype == "ARG"):
                    self.position += 1
                    continue
                break
        self.close("FUNC")
        return FormulaNode("function", token.value[:-1].upper(), tuple(args))

    def take(self):
        if self.position >= len(self.tokens):
            raise FormulaUnavailable("unsupported_expression")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def close(self, kind: str) -> None:
        token = self.take()
        if token.type != kind or token.subtype != "CLOSE":
            raise FormulaUnavailable("unsupported_expression")
