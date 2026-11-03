"""Complete keyed record fixtures shared by narrative and evidence tests."""


def _cell(address, value, fmt="General"):
    return {"cell": address, "value": value, "number_format": fmt}


def _source(amount="TotalPrice", quantity="Qty", category="Category", labels=None, values=None):
    labels = labels or ["Alpha", "Alpha", "Alpha", "Beta", "Beta", "Beta"]
    values = values or [20, 30, 10, 20, 10, 10]
    rows = [[_cell("A1", "Record ID"), _cell("B1", category), _cell("C1", amount),
             _cell("D1", quantity), _cell("E1", "UnitPrice")]]
    rows += [[_cell(f"A{i}", f"Entry-{i}"), _cell(f"B{i}", label),
              _cell(f"C{i}", value), _cell(f"D{i}", i - 1), _cell(f"E{i}", 3)]
             for i, (label, value) in enumerate(zip(labels, values), 2)]
    return {"sheets": [{"name": "Records", "business_facts": {"table_regions": [
        {"rows": rows, "rows_complete": True},
    ]}}]}


def _rows(context):
    return context["sheets"][0]["business_facts"]["table_regions"][0]["rows"]


def _quoted(text, label):
    return any(f"{left}{label}{right}" in text
               for left, right in [("'", "'"), ('"', '"'), ("‘", "’"), ("“", "”")])
