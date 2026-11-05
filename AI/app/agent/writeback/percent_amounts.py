"""A percentage the user states ("1.3%로 바꿔줘") is the number Excel stores, 0.013.

Excel keeps 1.3% as 0.013 and shows it with a percent format. A rule's amount may
arrive as "1.3%", or as 1.3 when the request wrote 1.3% for a percent-formatted
cell; written as is, the first becomes text and the second 130%. Both are read
here as the stored number. A bare amount the request did not write with % stays
as written, and text cells keep the text.
"""
import re
from decimal import Decimal

from app.agent.writeback.value_authorization import as_number

WRITTEN = re.compile(r"\s*([-+]?\d+(?:\.\d+)?)\s*%\s*")
STATED = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%")


def stored_amount(amount, cell, instruction) -> Decimal | None:
    """The number to store in a numeric cell, or None when the amount is not a number."""
    if isinstance(amount, bool):
        return None
    if isinstance(amount, str) and (written := WRITTEN.fullmatch(amount.replace(",", ""))):
        return Decimal(written[1]) / 100
    number = as_number(amount)
    if (number is not None and "%" in (cell.number_format or "")
            and number in {Decimal(value) for value in STATED.findall(instruction.replace(",", ""))}):
        return number / 100
    return number
