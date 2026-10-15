"""Small, safe subset of Excel display formatting used by canonical answers."""

import re
from dataclasses import dataclass

from app.services.insights.display.percent_format import scales_by_percent

_PLACEHOLDER = re.compile(r"[0#?]")
_QUOTED = re.compile(r'"([^"\r\n]*)"')
_CURRENCY = frozenset("$€£¥₩₹")
_UNSUPPORTED = re.compile(
    r"\?+\s*/\s*(?:\?+|\d+)|(?<!\[)(?:h{1,2}:m{1,2}|m{1,2}:s{1,2})|"
    r"[dmy]{1,4}[./-][dmy]{1,4}|e[+-]0+|@", re.I,
)

@dataclass(frozen=True)
class NumberFormat:
    minimum_decimals: int
    maximum_decimals: int
    prefix: str = ""
    suffix: str = ""
    percent: bool = False
    multiplier: int = 1
    divisor: int = 1
    mode: str = ""

def parse_number_format(number_format: object) -> NumberFormat:
    section = str(number_format or "General").split(";", 1)[0]
    minimum, maximum = _precision(section)
    percent = "%" in section
    prefix, suffix = _affixes(section, percent)
    return NumberFormat(
        minimum, maximum, prefix, suffix, percent,
        100 if percent and scales_by_percent(section) else 1,
        1000 ** _scale_commas(section),
        _display_mode(section),
    )

def display_value(value: object, spec: NumberFormat, fallback_unit: str = "") -> str:
    if spec.mode == "raw":
        return f"{spec.prefix}{_raw_number(value)}{spec.suffix or fallback_unit}"
    if spec.mode:
        return f"{spec.prefix}{_duration(float(value), spec.mode)}{spec.suffix}"
    suffix = spec.suffix or ("%" if spec.percent else fallback_unit)
    return f"{spec.prefix}{number_text(scaled_value(value, spec), spec)}{suffix}"

def scaled_value(value: object, spec: NumberFormat) -> float:
    return float(value) * spec.multiplier / spec.divisor

def number_text(value: float, spec: NumberFormat) -> str:
    rendered = f"{value:,.{spec.maximum_decimals}f}"
    if spec.maximum_decimals > spec.minimum_decimals and "." in rendered:
        whole, fraction = rendered.split(".", 1)
        fraction = fraction.rstrip("0")
        fraction += "0" * max(0, spec.minimum_decimals - len(fraction))
        rendered = f"{whole}.{fraction}" if fraction else whole
    return rendered

def delta_format(before: NumberFormat, after: NumberFormat) -> NumberFormat:
    if before.mode == "raw" or after.mode == "raw":
        return after if after.mode == "raw" else NumberFormat(0, 0, mode="raw")
    identity = lambda item: (
        item.prefix, item.suffix, item.divisor, item.mode, item.multiplier
    )
    if identity(before) == identity(after):
        return after
    return NumberFormat(after.minimum_decimals, after.maximum_decimals)

def _precision(section: str) -> tuple[int, int]:
    match = re.search(r"\.([0#?]+)", _without_literals(section))
    if not match:
        return (0, 2) if section.casefold() == "general" else (0, 0)
    decimals = match.group(1)
    return decimals.count("0"), len(decimals)

def _scale_commas(section: str) -> int:
    plain = _without_literals(section)
    positions = [match.end() for match in _PLACEHOLDER.finditer(plain)]
    if not positions:
        return 0
    match = re.match(r"\s*(,+)", plain[positions[-1] :])
    return len(match.group(1)) if match else 0

def _display_mode(section: str) -> str:
    plain = _QUOTED.sub("", section).casefold()
    if plain.strip() == "general" or _UNSUPPORTED.search(plain):
        return "raw"
    if re.search(r"\[h]\s*:mm\s*:ss", plain):
        return "hms"
    if re.search(r"\[h]\s*:mm", plain):
        return "hm"
    if re.search(r"\[m]\s*:ss", plain):
        return "ms"
    return "s" if "[s]" in plain else ""

def _raw_number(value: object) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    number = float(value)
    return f"{int(number):,}" if number.is_integer() else repr(number)

def _duration(days: float, kind: str) -> str:
    sign = "-" if days < 0 else ""
    seconds = int(abs(days) * 86_400 + 0.5)
    if kind == "s":
        return f"{sign}{seconds}"
    if kind == "ms":
        minutes, second = divmod(seconds, 60)
        return f"{sign}{minutes}:{second:02d}"
    if kind == "hm":
        minutes = int(abs(days) * 1_440 + 0.5)
        hour, minute = divmod(minutes, 60)
        return f"{sign}{hour}:{minute:02d}"
    hour, remainder = divmod(seconds, 3_600)
    minute, second = divmod(remainder, 60)
    return f"{sign}{hour}:{minute:02d}:{second:02d}"

def _affixes(section: str, percent: bool) -> tuple[str, str]:
    placeholder = _PLACEHOLDER.search(section)
    pivot = placeholder.start() if placeholder else len(section)
    prefix = suffix = ""
    for match in _QUOTED.finditer(section):
        literal = _safe_literal(match.group(1))
        if literal and literal != "%":
            if match.start() < pivot:
                prefix += literal
            else:
                suffix += literal
    for position, character in enumerate(section):
        if character not in _CURRENCY:
            continue
        if character == "$" and position > 0 and section[position - 1] == "[":
            continue
        prefix, suffix = (
            (character + prefix, suffix) if position < pivot
            else (prefix, suffix + character)
        )
        break
    if percent:
        suffix = suffix.removesuffix("%") + "%"
    return prefix, suffix

def _safe_literal(value: str) -> str:
    text = " ".join(value.split()).strip()
    safe = all(character.isalnum() or character in " %/._-" for character in text)
    return text if text and len(text) <= 12 and text[0] not in "=+@-" and safe else ""

def _without_literals(section: str) -> str:
    return _QUOTED.sub("", re.sub(r"\[[^]]*]", "", section))
