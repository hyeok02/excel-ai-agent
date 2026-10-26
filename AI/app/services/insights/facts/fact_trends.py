import re
from datetime import datetime

from app.services.insights.display.derived_metrics import derived_metric, magnitude_weight
from app.services.insights.display.display_quality import is_identifier_label
from app.services.insights.facts.series_scalars import consistent_metric, displayed_value, scalar, unit

MAX_TEXT_LENGTH = 120
MAX_IDENTITY_CELLS = 3
# 식별 행의 이름표가 대상을 가리키는지 판단하는 기준.
SUBJECT_LABEL = re.compile(
    r"(?:분석\s*)?대상|회사|기업|기관|\b(?:company|entity|focus)\b|►", re.I
)
NUMERIC_PATTERN = re.compile(r"-?[\d,]+(?:\.\d+)?%?")


def numeric_changes(records: list[dict[str, object]]) -> list[dict[str, object]]:
    dated = sorted(
        records,
        key=lambda record: date_value(record["values"][0]["value"]) or datetime.min,
    )
    if len(dated) < 2:
        return []
    earliest, latest = dated[0], dated[-1]
    old_by_label = _numbers_by_label(earliest)
    new_by_label = _numbers_by_label(latest)
    changes = []
    for label in [name for name in old_by_label if name in new_by_label]:
        if not consistent_metric(dated, label):
            continue
        old, new = old_by_label[label], new_by_label[label]
        if old == 0 or old == new and all(_numbers_by_label(row).get(label) == old for row in dated):
            continue
        change = {
            "metric": label,
            "earliest_period": earliest["values"][0]["value"],
            "earliest_value": old,
            "latest_period": latest["values"][0]["value"],
            "latest_value": new,
            "change": round(new - old, 4),
            "change_rate_percent": round((new - old) / abs(old) * 100, 2),
            "evidence": [earliest["location"], latest["location"]],
        }
        source_unit = next(unit(cell) for cell in earliest["values"][1:] if cell.get("label") == label)
        if source_unit:
            change["unit"] = source_unit
        changes.append(change)
    # 수치가 똑같은 항목이 둘 있으면 어느 쪽을 쓸지 정렬만으로는 갈리지 않는다.
    # 이름으로 먼저 줄을 세워 두면, 같은 파일을 다시 돌려도 같은 항목이 뽑힌다.
    named = sorted(changes, key=lambda item: item["metric"])
    return sorted(
        named, key=lambda item: (
            not derived_metric(item["metric"]),
            bool(re.search(r"\btotal\b|전체|합계|총합", item["metric"], re.I)),
            magnitude_weight(item["latest_value"]),
            abs(item["change_rate_percent"]),
        ), reverse=True
    )[:4]


def date_value(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _numbers_by_label(record: dict[str, object]) -> dict[str, float]:
    return {
        str(value["label"]): displayed_value(value)
        for value in record["values"][1:]
        if value.get("label")
        and not is_identifier_label(value["label"])
        and scalar(value["value"])
    }


def is_plain_text(value: object) -> bool:
    """수치도 날짜도 아닌, 이름표로 쓸 수 있는 짧은 문자열인지 판단한다."""
    text = str(value).strip()
    if not text or len(text) > MAX_TEXT_LENGTH:
        return False
    if NUMERIC_PATTERN.fullmatch(text):
        return False
    return date_value(text) is None


def is_identity_row(values: list[dict[str, object]]) -> bool:
    """'이름표 … 값' 형태로 대상을 적어 둔 행인지 행의 모양으로 판단한다.

    표 안의 데이터 셀에는 열 이름이 붙는다. 따라서 열 이름이 붙지 않은
    짧은 평문 행만 식별 행으로 보고, 마지막 칸을 대상 이름으로 읽는다.
    안내 문구가 앞에 붙어 세 칸이 되는 배치가 실제 워크북에서 흔하므로
    두 칸으로 제한하지 않는다.
    """
    if not 2 <= len(values) <= MAX_IDENTITY_CELLS:
        return False
    if any(value.get("label") for value in values):
        return False
    return all(is_plain_text(value.get("value")) for value in values)
