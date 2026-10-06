"""Name what a checklist checks: the items, the checks, and where it stalls."""
from app.services.insights.display.glossary import readable
from app.services.insights.facts.flag_columns import mark_of
from app.services.insights.narratives.narrative_values import number, subject_particle
from app.services.insights.narratives.table_dates import column as col

MAX_NAMED = 3
SHORT_NAME = 24


def subject_of(label, records):
    """
    'CVD #1'…'CVD #22'는 'CVD 설비'다 — 번호를 뺀 공통 머리말이 대상의 이름이다.

    열 이름('장비')만 쓰면 무엇을 점검한 표인지 끝내 드러나지 않는다.
    """
    if label is None:
        return "항목"
    values = _column_values(label, records)
    shared = _common_prefix(values)
    name = readable(label.get("value"))
    if not shared or shared in name or name in shared:
        return name
    return f"{shared} {name}"


def check_names(run):
    """List the checks by name: '5가지 항목'만으로는 무엇을 봤는지 알 수 없다."""
    names = [_short(cell.get("value")) for _, cell, _, _ in run]
    listed = ", ".join(f"‘{name}’" for name in names[:MAX_NAMED])
    if len(names) <= MAX_NAMED:
        return f"{listed} {number(len(names))}가지"
    return f"{listed} 등 {number(len(names))}가지"


def stalled_check(run, mark="x"):
    """
    표식이 갈리는 항목 중 'x'가 가장 많은 것이 지금 일이 멈춰 선 자리다.

    한 가지 표식만 적힌 항목은 비교할 것이 없어, 가장 많아도 알려 줄 내용이 없다.
    """
    varied = [(_negative(counts, mark), position, cell, counts)
              for position, cell, counts, _ in run if len(counts) > 1]
    if not varied:
        return ""
    count, _, cell, counts = max(varied, key=lambda found: (found[0], -found[1]))
    if not count:
        return ""
    written = next(key for key in counts if mark_of(key) == mark)
    name = _short(cell.get("value"))
    return (f"‘{name}’{subject_particle(name)} {written}인 건이 "
            f"{number(count)}건으로 가장 많습니다.")


def _negative(counts, mark):
    return sum(count for key, count in counts.items() if mark_of(key) == mark)


def _short(value):
    name = readable(value)
    head = name.split("(")[0].strip()
    return head if 0 < len(head) <= SHORT_NAME else name[:SHORT_NAME]


def _column_values(label, records):
    position = col(label)
    return [str(item["value"]) for record in records for item in record
            if col(item) == position and isinstance(item.get("value"), str)]


def _common_prefix(values):
    if len(values) < 2:
        return ""
    heads = [value.split() for value in values]
    shared = []
    for parts in zip(*heads):
        if len({part for part in parts}) != 1 or any(char.isdigit() for char in parts[0]):
            break
        shared.append(parts[0])
    return " ".join(shared)
