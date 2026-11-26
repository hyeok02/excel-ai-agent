"""A period the request moves a date by, and which way: '2주 미뤄줘' is +2 weeks, '사흘 앞당겨' is -3 days.

Weeks and days are the same length (2주 = 14일), as are years and months (1년 = 12개월), so a reading in either
unit is accepted. The direction must be written: 미루다·연장·늦추다 move later, 당기다 moves earlier.
"""
import re

NUMBER = {"한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5, "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10}
NAMED_DAYS = {"하루": 1, "이틀": 2, "사흘": 3, "나흘": 4, "닷새": 5, "열흘": 10}
UNITS = {"days": (r"일(?!요)|days?", 1), "weeks": (r"주일?|weeks?", 7), "months": (r"개월|달|months?", 1000),
         "years": (r"년|해|years?", 12000)}
LATER = re.compile(r"미뤄|미루|연장|늦춰|늦추|뒤로|delay|postpone|extend|push", re.I)
EARLIER = re.compile(r"당겨|당기|앞당|earlier|bring forward|move up", re.I)


def moved_by(instruction: str, amount: int, unit: str | None, sign: int) -> bool:
    if unit not in UNITS or not (LATER if sign > 0 else EARLIER).search(instruction):
        return False
    wanted = amount * UNITS[unit][1]
    stated = [NAMED_DAYS[word] for word in re.findall("|".join(NAMED_DAYS), instruction)]
    for name, (pattern, size) in UNITS.items():
        for count in re.findall(rf"(\d+|{'|'.join(NUMBER)})\s*(?:{pattern})", instruction, re.I):
            stated.append((NUMBER.get(count) or int(count)) * size)
    return wanted in stated
