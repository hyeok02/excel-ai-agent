"""Independent source populations for grouped and ranked offline regressions."""
from tests.support.large_workbook_fixtures import parsed, plan_for, workbook


def records():
    return [
        ["Record", "Amount", "Department", "State"],
        ["First", 9, "Alpha", "active"],
        ["Low", -8, "Alpha", "inactive"],
        ["Third", 15, "Beta", "active"],
        ["Fourth", 15, "Alpha", "active"],
        ["Fifth", 8, "Beta", "inactive"],
        ["Sixth", 1, "Beta", "active"],
        ["Seventh", -3, "Gamma", "active"],
        ["Late", -20, "Gamma", "active"],
        ["Winner", 900, "Delta", "inactive"],
        ["Tail", 70, "Delta", "active"],
    ]


def source(matrix=None, limits=None):
    return parsed(workbook({"Records": records() if matrix is None else matrix}), limits=limits)


def raw_plan(summary, **changes):
    options = dict(operation="row_list", columns=("A", "B"), order_by="B", limit=2)
    options.update(changes)
    return plan_for(summary, **options)


def grouped_plan(summary, **changes):
    options = dict(group_by=["C"], statistic="sum")
    options.update(changes)
    return plan_for(summary, **options)


def answer_rows(answer):
    """Strip the scope line before asserting source labels or row order."""
    return [line for line in answer.answer.splitlines() if not line.startswith("조건:")]


def line_with(answer, label):
    matches = [line for line in answer_rows(answer) if label in line]
    assert len(matches) == 1, answer.model_dump()
    return matches[0]


def assert_before(answer, first, second):
    lines = "\n".join(answer_rows(answer))
    assert lines.index(first) < lines.index(second), answer.model_dump()
