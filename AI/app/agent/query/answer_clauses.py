"""Validate small claims, but remove unsupported prose only as complete units."""
import re

from app.agent.query.answer_segments import TABLE_SEPARATOR, answer_units, validation_clauses

INCREASE = re.compile(r"증가|증대|늘어|늘었|상승|increas|grew|rose|growth", re.I)
DECREASE = re.compile(r"감소|축소|줄어|줄었|하락|decreas|fell|declin|drop", re.I)
STRUCTURE = re.compile(r"^\s*#{1,6}\s+")
PREDICATE = re.compile(r"(?:습니다|입니다|한다|된다|이다|했다|있다|없다)[.!?]?$")
ENGLISH_PREDICATE = re.compile(
    r"\S+\s+(?:is|are|was|were|has|have|had|contains?|equals?)\s+\w|"
    r"\S+\s+(?:increased|decreased|grew|fell|rose|declined|changed|remained)\b", re.I
)


def clauses(text: str) -> list[str]:
    return validation_clauses(text)


def stated_direction(text: str) -> str | None:
    """절이 증감 중 한쪽만 말하고 있으면 그 방향을 돌려준다."""
    increase = bool(INCREASE.search(text))
    decrease = bool(DECREASE.search(text))
    if increase == decrease:
        return None
    return "increase" if increase else "decrease"


def supported_clauses(text: str, verified) -> tuple[str, bool]:
    """Keep original complete claims; never turn label fragments into sentences."""
    units = answer_units(text)
    accepted = [all(verified(part) for part in clauses(unit)) for unit in units]
    if all(accepted):
        return text, False
    kept = {
        index for index, (unit, valid) in enumerate(zip(units, accepted))
        if valid and _complete_claim(unit)
    }
    for index, unit in enumerate(units):
        if not TABLE_SEPARATOR.match(unit) or not index:
            continue
        rows = []
        for following in range(index + 1, len(units)):
            if not units[following].lstrip().startswith("|"):
                break
            rows.append(following)
        kept.discard(index - 1)
        if accepted[index - 1] and any(row in kept for row in rows):
            kept.update((index - 1, index))
        else:
            kept.difference_update(rows)
    # Keep the original separators, punctuation, bullets and table formatting.
    return "".join(unit for index, unit in enumerate(units) if index in kept).strip(), True


def _complete_claim(unit: str) -> bool:
    value = unit.strip()
    if not value or STRUCTURE.match(value) or TABLE_SEPARATOR.match(value) or value.endswith(":"):
        return False
    if value.startswith("|"):
        return len([cell for cell in value.strip("|").split("|") if cell.strip()]) > 1
    value = re.sub(r"^\s*(?:[-+*]|\d+[.)])\s+", "", value)
    if re.search(r"\S\s*[:：→]\s*\S", value):
        return True
    return bool(PREDICATE.search(value) or ENGLISH_PREDICATE.search(value))
