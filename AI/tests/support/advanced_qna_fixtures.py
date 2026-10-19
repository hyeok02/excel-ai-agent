"""Independent inputs for common aggregate, ratio and partition queries."""
from tests.support.large_workbook_fixtures import parsed, plan_for, workbook


def records():
    return [
        ["Record", "Amount", "Department", "Customer", "State"],
        ["Aone", 40, "Alpha", "Client1", "active"],
        ["Atwo", 20, "Alpha", "Client2", "active"],
        ["Bone", 30, "Beta", "Client1", "active"],
        ["Btwo", 10, "Beta", "Client3", "active"],
        ["Athree", 10, "Alpha", "Client1", "inactive"],
        ["Bthree", 50, "Beta", "Client4", "inactive"],
        ["Cone", 25, "Gamma", "Client2", "active"],
        ["Afour", 5, "Alpha", "Client5", "active"],
    ]


def source(matrix=None, *, limits=None):
    return parsed(workbook({"Records": records() if matrix is None else matrix}), limits=limits)


def condition(value, *, column="B", operator="greater_than", target="aggregate", unit="raw"):
    return {"column_id": column, "operator": operator, "value": value,
            "target": target, "value_unit": unit}


def group_plan(summary, **changes):
    options = dict(group_by=["C"], statistic="sum")
    options.update(changes)
    return plan_for(summary, **options)


def distinct_plan(summary, **changes):
    options = dict(operation="distinct_count", columns=("D",))
    options.update(changes)
    return plan_for(summary, **options)


def partition_plan(summary, **changes):
    options = dict(operation="row_list", columns=("A", "B"), group_by=["C"],
                   order_by="B", per_group_limit=2)
    options.update(changes)
    return plan_for(summary, **options)


def checked(answer, *, scan=None):
    assert answer.status in {"answered", "limited"}, answer.model_dump()
    assert answer.verification.level == "request_checked", answer.model_dump()
    if scan is not None:
        assert ("full_source_scan" in answer.verification.checks) == scan, answer.model_dump()


def result_lines(answer):
    return [line for line in answer.answer.splitlines() if not line.startswith("조건:")]


def group_line(answer, group):
    matches = [line for line in result_lines(answer) if has_group(line, group)]
    assert len(matches) == 1, answer.model_dump()
    return matches[0]


def has_group(text, group, header="Department"):
    return f'{header}: "{group}"' in text or f"{header}: {group} —" in text
