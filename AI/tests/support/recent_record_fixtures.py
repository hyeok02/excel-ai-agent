"""Small complete records and arbitrary worksheet context builders."""


def cell(address, value, fmt="General"):
    return {"cell": address, "value": value, "number_format": fmt}


def context(rows, name="Data", complete=True):
    return {"sheets": [{"name": name, "business_facts": {"table_regions": [
        {"rows": rows, "rows_complete": complete},
    ]}}]}


def record_rows():
    header = [cell("A1", "Record ID"), cell("B1", "Group"), cell("C1", "TotalAmount"),
              cell("D1", "UnitPrice")]
    return [header] + [[cell(f"A{i}", f"R{i}"), cell(f"B{i}", "North" if i <= 4 else "South"),
                        cell(f"C{i}", 10 if i <= 4 else 5), cell(f"D{i}", 2)] for i in range(2, 7)]
