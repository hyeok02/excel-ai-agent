"""Source identity checks prevent row rankings from masquerading as people rankings."""
from app.agent.query.grouped_tabular_state import typed_key

MAX_IDENTITIES = 100000
MAX_IDENTITY_CHARACTERS = 8_000_000


class PartitionIdentities:
    def __init__(self, columns):
        self.columns = columns
        self.seen = set()
        self.characters = 0

    def add(self, partition, row):
        if not self.columns:
            return True
        components = []
        characters = 0
        for column in self.columns:
            value = row.values.get(column)
            if value is None or isinstance(value, str) and not value.strip():
                return False
            part = typed_key(value, row.number_formats.get(column, "General"))
            if part is None:
                return False
            components.append(part[0])
            characters += len(part[1])
        key = (partition, tuple(components))
        if (key in self.seen or len(self.seen) >= MAX_IDENTITIES
                or self.characters + characters > MAX_IDENTITY_CHARACTERS):
            return False
        self.seen.add(key)
        self.characters += characters
        return True
