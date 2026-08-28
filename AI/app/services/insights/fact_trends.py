from datetime import datetime


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
    for label in old_by_label.keys() & new_by_label.keys():
        old, new = old_by_label[label], new_by_label[label]
        if old == 0 or old == new:
            continue
        changes.append(
            {
                "metric": label,
                "earliest_period": earliest["values"][0]["value"],
                "earliest_value": old,
                "latest_period": latest["values"][0]["value"],
                "latest_value": new,
                "change": round(new - old, 4),
                "change_rate_percent": round((new - old) / abs(old) * 100, 2),
                "evidence": [earliest["location"], latest["location"]],
            }
        )
    return sorted(
        changes, key=lambda item: abs(item["change_rate_percent"]), reverse=True
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
        str(value["label"]): float(value["value"])
        for value in record["values"][1:]
        if value.get("label") and isinstance(value["value"], (int, float))
    }
