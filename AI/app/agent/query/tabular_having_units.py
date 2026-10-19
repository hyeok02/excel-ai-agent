"""Map explicit threshold units to proven source-storage units, never guess FX."""
import re
from decimal import Decimal, localcontext

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.metric_observation_units import _currency, _magnitude, _CURRENCIES

_SCALES = {"천": Decimal(1000), "만": Decimal(10000), "백만": Decimal(1000000),
           "천만": Decimal(10000000), "억": Decimal(100000000), "십억": Decimal(1000000000),
           "조": Decimal(1000000000000)}
_ENGLISH = {"thousand": Decimal(1000), "million": Decimal(1000000),
            "billion": Decimal(1000000000), "trillion": Decimal(1000000000000)}
_KOREAN_CURRENCY = {"달러": "달러", "유로": "유로", "엔": "엔", "파운드": "파운드"}


def source_threshold(value, match, table, column, target):
    """None means unproven units; returned Decimal is in stored-cell units."""
    fields = match.groupdict()
    currency_tokens = [fields.get(key) for key in ("currency", "currency_before") if fields.get(key)]
    currencies = {_currency(token) or _KOREAN_CURRENCY.get(token, "") for token in currency_tokens}
    if "" in currencies or len(currencies) > 1:
        return None
    currency = next(iter(currencies), "")
    english = (fields.get("magnitude") or "").casefold().rstrip("s")
    if english:
        with localcontext() as context:
            context.prec = max(40, len(value.as_tuple().digits) + 20)
            value *= _ENGLISH[english]
    explicit_scale = bool(english or re.search(r"[십백천만억조]", fields["number"]))
    percent = bool(fields.get("unit"))
    if target == "share":
        return None if currency or explicit_scale else value
    if column is None:
        return None if currency or percent else value
    header = next(item.header for item in table.columns if item.id == column)
    magnitude, source_currency = _magnitude(header), _source_currency(header)
    styles = [parse_number_format(row.number_formats.get(column, "General")) for row in table.rows]
    identities = {(style.prefix, style.suffix, style.percent, style.multiplier, style.divisor) for style in styles}
    if len(identities) > 1:
        return None
    style_currency = _source_currency(styles[0].prefix + styles[0].suffix) if styles else ""
    if source_currency is None or style_currency is None:
        return None
    if source_currency and style_currency and not _compatible(style_currency, source_currency):
        return None
    source_currency = source_currency or style_currency
    if currency and (not source_currency or not _compatible(currency, source_currency)):
        return None
    if percent and (currency or explicit_scale or magnitude):
        return None
    if percent and any(style.divisor != 1 for style in styles):
        return None
    if currency and ("%" in header or any(style.percent for style in styles)):
        return None
    # Report-level scale captions without a source-column proof are ambiguous.
    contextual = {_magnitude(str(caption)) for _, caption in table.context} - {""}
    if contextual and contextual != {magnitude}:
        return None
    if not currency and not explicit_scale:
        return value
    # Display scaling can contradict a header scale; do not infer a conversion.
    if any(style.divisor != 1 or style.multiplier != 1 for style in styles):
        return None
    if magnitude:
        scale = _SCALES.get(magnitude)
        with localcontext() as context:
            context.prec = max(40, len(value.as_tuple().digits) + abs(value.as_tuple().exponent) + 20)
            return value / scale if scale else None
    return value


def _compatible(requested, source):
    return requested == source or requested == "달러" and source.endswith("달러")


def _source_currency(text):
    values = {_currency(text)} - {""}
    for name, value in (_CURRENCIES | _KOREAN_CURRENCY).items():
        if re.search(r"(?<![a-z가-힣])" + re.escape(name) + r"(?![a-z가-힣])", text, re.I):
            values.add(value)
    for symbol, value in {"$": "달러", "€": "유로", "£": "파운드", "₩": "원"}.items():
        if symbol in text:
            values.add(value)
    if len(values) > 1 and all(value.endswith("달러") for value in values):
        values.discard("달러")
    return None if len(values) > 1 else next(iter(values), "")
