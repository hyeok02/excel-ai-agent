"""Which rounding a request asks for and to how many places: '소수 첫째 자리에서 반올림' keeps 0 places.

Places count digits kept after the point: 2 for '소수 둘째 자리까지', 0 for '정수로', -2 for '백원 단위로' or
'십의 자리에서 반올림'. Every phrase found is returned; a request with none names no places at all.
"""
import re

ROUNDING = {"round": re.compile(r"반올림|\bround(?!\s*(?:up|down))", re.I),
            "round_up": re.compile(r"(?<!반)올림|round\s*up|ceil", re.I),
            "round_down": re.compile(r"내림|버림|절사|round\s*down|floor|truncat", re.I)}
ORDINAL = {"첫": 1, "둘": 2, "셋": 3, "넷": 4, "다섯": 5}
DIGIT = {"일": 0, "십": 1, "백": 2, "천": 3, "만": 4}
NEAREST = {"integer": 0, "whole": 0, "ten": -1, "hundred": -2, "thousand": -3}


def rounding_places(instruction: str) -> set[int]:
    places = set()
    for count, where in re.findall(r"소수\s*점?\s*(?:이하\s*)?(첫|둘|셋|넷|다섯|\d+)\s*(?:번?째)\s*자리\s*(에서|까지|로)?",
                                   instruction):
        number = ORDINAL.get(count) or int(count)
        places.add(number - 1 if where == "에서" else number)
    places |= {int(count) for count in re.findall(r"소수\s*점?\s*(?:이하\s*)?(\d+)\s*자리(?!\s*에서)", instruction)}
    for unit, where in re.findall(r"(일|십|백|천|만)의\s*자리\s*(에서|까지|로)?", instruction):
        places.add(-(DIGIT[unit] + 1) if where == "에서" else -DIGIT[unit])
    for small, large in re.findall(r"(십|백|천)?\s*(만|억)?\s*원?\s*단위", instruction):
        if small or large:  # 백원 단위 -2, 천만원 단위 -7
            places.add(-(DIGIT.get(small, 0) + {"만": 4, "억": 8}.get(large, 0)))
    if re.search(r"정수|소수\s*점?\s*(?:이하\s*)?(?:없이|버림|제거)|whole\s+numbers?|\bintegers?\b", instruction, re.I):
        places.add(0)
    places |= {int(count) for count in re.findall(r"(\d+)\s*decimal", instruction, re.I)}
    places |= {NEAREST[word] for word in re.findall(r"nearest\s+(integer|whole|ten|hundred|thousand)", instruction, re.I)}
    return places
