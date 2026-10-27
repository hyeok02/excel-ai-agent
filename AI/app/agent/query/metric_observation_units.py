"""Units for an observation come from its format and local source captions."""

import re
from dataclasses import dataclass

from app.agent.query.comparison_value_format import people_unit
from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.metric_observations import MetricObservation, _column
from app.agent.query.metric_unit_settings import source_settings, explicit_row_settings
from app.agent.query.trend_row_metadata import UNIT_HEADERS

_MAGNITUDES = {
    "million": "백만", "millions": "백만", "백만": "백만",
    "billion": "십억", "billions": "십억", "십억": "십억",
    "thousand": "천", "thousands": "천", "천": "천",
}
_CURRENCIES = {
    "u.s. dollar": "미국 달러", "us dollar": "미국 달러", "usd": "미국 달러",
    "euro": "유로", "eur": "유로", "korean won": "원", "krw": "원",
    "japanese yen": "엔", "jpy": "엔", "british pound": "파운드", "gbp": "파운드",
}


@dataclass(frozen=True)
class ObservationUnit:
    suffix: str
    identity: tuple
    references: tuple
    known: bool


def observation_unit(observation: MetricObservation, rows) -> ObservationUnit:
    spec = parse_number_format(observation.value.number_format)
    style_identity = (spec.prefix, spec.suffix, spec.percent, spec.multiplier, spec.divisor)
    if spec.percent:
        return ObservationUnit("", style_identity, (), True)
    if unit := people_unit("", observation.label.value):
        explicit, row_refs = explicit_row_settings(observation, _currency, _magnitude, {"magnitude"})
        label_magnitude = _magnitude(str(observation.label.value))
        if explicit is None or (explicit.get("magnitude") and label_magnitude
                                and explicit["magnitude"] != label_magnitude):
            return ObservationUnit("", ("conflicting_units", *style_identity), row_refs, False)
        suffix = (explicit.get("magnitude") or label_magnitude) + unit
        return ObservationUnit(suffix, (suffix, *style_identity), (observation.label, *row_refs), True)
    label = str(observation.label.value).casefold()
    if "%" in label:
        if _currency(label) or _currency(spec.prefix + spec.suffix) or spec.suffix.strip() not in {"", "%"}:
            return ObservationUnit("", ("conflicting_units", *style_identity), (observation.label,), False)
        # A percentage unit in the source header with a numeric 0.0 format
        # means stored percentage points, not a fraction requiring x100.
        return ObservationUnit("%", ("stored_percent_points", *style_identity), (observation.label,), True)
    # A source amount caption must not turn a ratio into dollars.
    if re.search(r"%|\bratio\b|\byield\b|\bgrowth\b|\bmargin\b|\bmultiple\b| / ", label):
        return ObservationUnit("", style_identity, (), False)
    relevant = [row for row in rows if row.sheet_name == observation.value.sheet_name]
    caption = observation.label if _currency(label) or _magnitude(label) else _caption(observation, relevant)
    currency, magnitude, references = source_settings(relevant, observation, _currency, _magnitude)
    explicit, row_refs = explicit_row_settings(observation, _currency, _magnitude)
    if explicit is None:
        return ObservationUnit("", ("conflicting_units", *style_identity), row_refs, False)
    currency, magnitude = explicit.get("currency", currency), explicit.get("magnitude", magnitude)
    if explicit:
        inherited = [cell for offset in range(0, len(references), 2)
                     if UNIT_HEADERS.get(str(references[offset].value).strip().casefold()) not in explicit
                     for cell in references[offset:offset + 2]]
        references = [*row_refs, *inherited]
    if caption is not None:
        text = str(caption.value)
        local_currency = _currency(text)
        local_magnitude = _magnitude(text)
        if (explicit.get("currency") and local_currency and local_currency != currency
                and not (local_currency == "달러" and currency.endswith("달러"))
                or explicit.get("magnitude") and local_magnitude and local_magnitude != magnitude):
            return ObservationUnit("", ("conflicting_units", *style_identity), (*row_refs, caption), False)
        currency = currency if local_currency == "달러" and currency else local_currency or currency
        magnitude = local_magnitude or magnitude
        references.append(caption)
    if not currency and not magnitude:
        return ObservationUnit("", style_identity, (), bool(spec.prefix or spec.suffix))
    style_currency = _currency(spec.prefix + spec.suffix)
    compatible_dollar = style_currency == "달러" and currency.endswith("달러")
    if style_currency and currency and style_currency != currency and not compatible_dollar:
        return ObservationUnit("", ("conflicting_units", currency, *style_identity), tuple(references), False)
    if re.search(r"\beps\b|per\s+share|주당", label):
        magnitude = ""
    suffix = " ".join(part for part in (magnitude, currency) if part)
    return ObservationUnit(suffix, (suffix, *style_identity), tuple(dict.fromkeys(references)), True)


def _caption(observation, rows):
    candidates = []
    period_row = int(re.search(r"\d+", observation.period_cell.address)[0])
    for row in rows:
        if not 0 <= period_row - row.row_number <= 30:
            continue
        for cell in row.cells:
            if not isinstance(cell.value, str):
                continue
            text = cell.value
            if _magnitude(text) and (_currency(text) or re.search(r"\bin\b|단위", text, re.I)):
                if _column(cell) <= _column(observation.value):
                    candidates.append((row.row_number, _column(cell), cell))
    return max(candidates, key=lambda item: item[:2])[2] if candidates else None


def _currency(value):
    normalized = value.casefold().strip()
    for name, text in _CURRENCIES.items():
        if re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", normalized):
            return text
    for symbol, name in {"$": "달러", "€": "유로", "£": "파운드", "₩": "원"}.items():
        if symbol in value:
            return name
    return "원" if re.search(r"(?:백만|천만|천|만|억|조)원|(?<![가-힣])원(?:\W|$)", value) else ""


def _magnitude(value):
    if re.search(r"\$\s*M\b", value, re.I):
        return "백만"
    if re.search(r"\$\s*B\b", value, re.I):
        return "십억"
    if re.search(r"\$\s*0{3}(?!0)|\b(?:USD|EUR|KRW)\s*0{3}\b", value, re.I):
        return "천"
    if match := re.search(r"(백만|천만|천|만|억|조)원", value):
        return match[1]
    for token, text in _MAGNITUDES.items():
        if re.search(r"(?<![a-z가-힣])" + re.escape(token) + r"(?![a-z가-힣])", value, re.I):
            return text
    return ""
