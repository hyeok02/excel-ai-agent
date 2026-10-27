import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

NUMBER_PATTERN = re.compile(
    r"(?<![\w])-?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?"
)
PERCENT_SCALE = Decimal("0.01")


@dataclass(frozen=True)
class NumberToken:
    raw: str
    # (값, 그 값을 얻으려고 적힌 숫자에 곱한 배율). 배율을 같이 들고 있어야
    # 반올림 허용 오차도 같은 배율로 맞출 수 있다.
    values: tuple[tuple[Decimal, Decimal], ...]
    decimal_places: int


def numbers(value: str) -> set[Decimal]:
    return {number for token in _number_tokens(value) for number, _ in token.values}


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
        # Scientific notation expresses precision at its exponent, too.
        # Treating 1e-6 as an integer gave it a 0.5 tolerance and could certify
        # an unrelated fractional source value.
        decimal_places = -number.as_tuple().exponent
        suffix = value[match.end() :]
        scale = _magnitude_scale(suffix)
        values = {(number, Decimal(1))}
        if scale is not None:
            values.add((number * scale, scale))
        if _is_percent(suffix):
            values.add((number / 100, PERCENT_SCALE))
        tokens.append(
            NumberToken(
                raw=normalized,
                values=tuple(sorted(values)),
                decimal_places=decimal_places,
            )
        )
    return tokens


def _matches_candidate(token: NumberToken, candidates: set[Decimal]) -> bool:
    """
    적힌 소수점 자리수에서 나온 허용 오차를, 비교하는 값의 배율에 맞춰 쓴다.

    배율을 무시하면 정수용 오차 0.5가 100으로 나눈 값에도 그대로 적용된다.
    0.07과 0.08의 차이 0.01이 0.5 안에 들어와, 원본이 7%인데 8%라고 적어도
    근거가 있다고 통과했다. 실제로 7% 하나만 있는 원본에서 0%부터 57%까지
    58가지 주장이 전부 통과했다.
    """
    written_tolerance = Decimal("0.5") * (Decimal(10) ** -token.decimal_places)
    for value, scale in token.values:
        if value in candidates:
            return True
        tolerance = written_tolerance * scale
        if any(abs(candidate - value) <= tolerance for candidate in candidates):
            return True
    return False


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
