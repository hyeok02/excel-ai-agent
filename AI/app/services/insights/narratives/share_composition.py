"""Tell a whole from its parts before comparing shares.

A source table often lists a total next to its breakdown ("All Institutions"
above "Institutions - Investment Managers"). Comparing those two as peers ("the
total is 9.81%p higher") misreads the table. A row is the whole when its quantity
equals the sum of every other row's quantity; a row whose name, without words
like "all/total", is inside another row's name is at least not that row's peer.
"""
from decimal import Decimal
import re

_WHOLE_WORDS = re.compile(r"\b(?:all|total|overall|aggregate)\b|전체|합계|총", re.I)
SUM_TOLERANCE = Decimal("0.001")


def whole_of(items):
    """The one row whose quantity is the sum of all the others, or None."""
    total = sum((item["quantity"] for item in items), Decimal(0))
    wholes = [item for item in items if len(items) > 2
              and abs(total - 2 * item["quantity"]) <= item["quantity"] * SUM_TOLERANCE]
    return wholes[0] if len(wholes) == 1 else None


def nested(outer, inner):
    """'All Institutions' names a group that 'Institutions - Banks' belongs to."""
    core = " ".join(_WHOLE_WORDS.sub(" ", outer["name"]).split()).casefold()
    return bool(core) and core != inner["name"].casefold() and core in inner["name"].casefold()


def share_text(*items):
    """Shares compared in one sentence keep the same number of decimals (56.00%, 65.81%)."""
    places = max(_places(item) for item in items)
    return [f"{item['share']:,.{places}f}%" for item in items]


def _places(item):
    tolerance = item["tolerance"] * 2
    return max(0, min(2, -tolerance.normalize().as_tuple().exponent)) if tolerance else 0
