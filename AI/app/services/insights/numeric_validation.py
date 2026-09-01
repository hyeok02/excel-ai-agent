import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

NUMBER_PATTERN = re.compile(
    r"(?<![\w])-?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?"
)


@dataclass(frozen=True)
class NumberToken:
    raw: str
    values: tuple[Decimal, ...]
    decimal_places: int


def numbers(value: str) -> set[Decimal]:
    return {number for token in _number_tokens(value) for number in token.values}


def unmatched_numbers(value: str, candidates: set[Decimal]) -> set[str]:
    return {
        token.raw
        for token in _number_tokens(value)
        if not _matches_candidate(token, candidates)
    }


def _number_tokens(value: str) -> list[NumberToken]:
    tokens = []
    for match in NUMBER_PATTERN.finditer(value):
        raw = match.group(0).replace(",", "")
        normalized = raw.lstrip("-")
        try:
            number = abs(Decimal(normalized))
        except InvalidOperation:
            continue
        decimal_places = len(normalized.partition(".")[2])
        suffix = value[match.end() :]
        scale = _magnitude_scale(suffix)
        values = {number}
        if scale is not None:
            values.add(number * scale)
        if _is_percent(suffix):
            values.add(number / 100)
        tokens.append(
            NumberToken(
                raw=normalized,
                values=tuple(values),
                decimal_places=decimal_places,
            )
        )
    return tokens


def _matches_candidate(token: NumberToken, candidates: set[Decimal]) -> bool:
    if any(value in candidates for value in token.values):
        return True
    rounding_tolerance = Decimal("0.5") * (Decimal(10) ** -token.decimal_places)
    return any(
        abs(candidate - value) <= rounding_tolerance
        for value in token.values
        for candidate in candidates
    )


def _magnitude_scale(suffix: str) -> Decimal | None:
    normalized = suffix.lstrip().casefold()
    scales = (
        ("trillion", Decimal("1e12")),
        ("billion", Decimal("1e9")),
        ("million", Decimal("1e6")),
        ("thousand", Decimal("1e3")),
        ("백만", Decimal("1e6")),
        ("조", Decimal("1e12")),
        ("억", Decimal("1e8")),
        ("만", Decimal("1e4")),
        ("천", Decimal("1e3")),
    )
    return next((scale for label, scale in scales if normalized.startswith(label)), None)


def _is_percent(suffix: str) -> bool:
    normalized = suffix.lstrip().casefold()
    return normalized.startswith(("%", "퍼센트", "percent"))
