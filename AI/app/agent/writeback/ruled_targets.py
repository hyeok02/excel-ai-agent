"""Cells a source-checked rule chose: only their values still need the request."""


class RuledTargets:
    """Rows and column come from a rule checked against the source; values still need the request."""

    def __init__(self, instruction, copied=None):
        # Several rules share one request ("10% 올리고 ... 5% 내려줘"), so each value is
        # checked against every stated value and calculation, not only the last clause.
        self.value_part = instruction
        self.copied = copied or {}  # cells set to another column's value, with where it came from

    def instruction_for(self, cell):
        return self.value_part, None

    def missing_risks(self, changes):
        return []
