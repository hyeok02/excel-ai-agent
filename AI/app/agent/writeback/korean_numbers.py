"""Korean amounts written with several units, read as one number: '4천5백만원' is 45,000,000.

'5천만', '1억2천만', '4천5백만' put 천·백·십 inside 만·억·조. A reader taking one unit at a time sees 5천 and
then a stray 만. Such spans are rewritten as plain digits before the request's numbers are read; an amount with
a single unit ('1억', '300만') is left to the readers that already take it.
"""
import re

SMALL = {"십": 10, "백": 100, "천": 1000}
LARGE = {"만": 10 ** 4, "억": 10 ** 8, "조": 10 ** 12}
SPAN = re.compile(r"(?<![\d.,])(?:\d[\d,]*\s*)?(?:[십백천만억조]\s*(?:\d[\d,]*\s*)?){2,}(?<=[십백천만억조\d])")
TOKEN = re.compile(r"(\d[\d,]*)?\s*([십백천만억조])|(\d[\d,]*)$")


def plain_numbers(text: str) -> str:
    return SPAN.sub(_digits, text)


def _digits(match):
    span = match.group(0).rstrip()
    total = section = 0
    for number, unit, tail in TOKEN.findall(span.replace(" ", "")):
        amount = int(number.replace(",", "")) if number else None
        if tail:
            section += int(tail.replace(",", ""))
        elif unit in SMALL:
            section += (amount or 1) * SMALL[unit]
        else:
            total += (section + (amount or 0) or 1) * LARGE[unit]
            section = 0
    return str(total + section) + match.group(0)[len(span):]
