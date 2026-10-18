"""Bounded full-scan witnesses for request guards, not a population sample."""
from app.agent.query.tabular_request_categories import value_matches

MAX_WITNESS_ROWS = 512
MAX_WITNESS_CELLS = 50_000
MAX_WITNESS_CHARACTERS = 2_000_000


class RequestWitnesses:
    def __init__(self, question, plan):
        self.question = question
        self.filters = {str(condition.value).casefold() for condition in plan.filters}
        self.rows, self.keys, self.cells, self.characters = [], set(), 0, 0

    def add(self, row):
        keys = {(column, "format", row.number_formats.get(column, "General")) for column in row.values}
        for column, value in row.values.items():
            if (str(value).casefold() in self.filters or isinstance(value, str)
                    and value_matches(self.question, value)):
                keys.add((column, type(value).__name__, str(value)))
        if keys <= self.keys:
            return True
        size = sum(len(str(value)) for value in row.values.values())
        if (len(self.rows) >= MAX_WITNESS_ROWS or self.cells + len(row.values) > MAX_WITNESS_CELLS
                or self.characters + size > MAX_WITNESS_CHARACTERS):
            return False
        self.keys.update(keys)
        self.rows.append(row)
        self.cells += len(row.values)
        self.characters += size
        return True
