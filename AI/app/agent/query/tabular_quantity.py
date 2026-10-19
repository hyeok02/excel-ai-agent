"""Decimal mixed-digit Korean quantities with explicit positional unit groups."""
import re
from decimal import Decimal, localcontext

_SMALL = {"십": Decimal(10), "백": Decimal(100), "천": Decimal(1000)}
_LARGE = {"만": Decimal(10000), "억": Decimal(100000000), "조": Decimal(1000000000000)}


def parse_quantity(text):
    negative = text.strip().startswith("-")
    tokens = re.findall(r"\d[\d,]*(?:\.\d+)?|[십백천만억조]", text.lstrip("-"))
    if not tokens:
        return None
    with localcontext() as context:
        context.prec = max(40, len(text) + 20)
        total = subtotal = Decimal(0)
        number = None
        previous_small, previous_large = Decimal(10000), Decimal(10000000000000)
        for token in tokens:
            if token in _SMALL:
                unit = _SMALL[token]
                if unit >= previous_small:
                    return None
                subtotal += (number if number is not None else 1) * unit
                previous_small, number = unit, None
            elif token in _LARGE:
                unit = _LARGE[token]
                if unit >= previous_large or number is None and subtotal == 0:
                    return None
                total += (subtotal + (number if number is not None else 0)) * unit
                subtotal, number = Decimal(0), None
                previous_large, previous_small = unit, Decimal(10000)
            else:
                if number is not None:
                    return None
                number = Decimal(token.replace(",", ""))
        result = total + subtotal + (number if number is not None else 0)
        return -result if negative else result
