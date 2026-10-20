"""Bind a derived operation to actual source labels, not workbook identities."""
from dataclasses import dataclass
import re

from app.agent.query.trend_labels import trend_label_spellings

GROWTH = re.compile(r"증감률|증가율|감소율|성장률|\b(?:growth\s+rate|percentage\s+change|percent\s+change)\b", re.I)
SHARE = re.compile(r"비중|점유율|비율|\b(?:share|ratio|proportion|percentage)\b", re.I)
YOY = re.compile(r"전년\s*(?:동기|동월)?\s*(?:대비)?|작년\s*같은\s*(?:기간|달)\s*(?:대비)?|\b(?:yoy|year[- ]over[- ]year)\b", re.I)
MOM = re.compile(r"전월\s*(?:대비)?|\b(?:mom|month[- ]over[- ]month)\b", re.I)
PREVIOUS = re.compile(r"이전\s*(?:관측(?:값|일)?|시점|기간)\s*(?:대비)?|직전\s*(?:관측(?:값|일)?|시점|기간)?\s*(?:대비)?|\bprevious\s+(?:observation|period)\b", re.I)
TEMPORAL = re.compile(r"추이|추세|흐름|기간별|시점별|월별|연도별|변화|변동|변했|증가|감소|늘었|줄었|\b(?:trend|over\s+time|change)\b", re.I)


@dataclass(frozen=True)
class DerivedRequest:
    kind: str
    labels: tuple[str, ...]
    basis: str = "previous"
    decrease: bool = False
    component: bool = False


def metric_tokens(question, candidates):
    labels = {str(cell.value) for item in candidates
              for cell in ([item.observations[0].label] if item.observations else item.context[:1])}
    remaining, selected = question, []
    for label in sorted(labels, key=lambda value: max(map(len, trend_label_spellings(value))), reverse=True):
        marker = f"__metric{len(selected)}__"
        changed = remaining
        for spelling in trend_label_spellings(label):
            tokens = re.findall(r"[a-z0-9_가-힣]+", spelling, re.I)
            if tokens:
                pattern = r"(?<![a-z0-9_가-힣])" + r"[^a-z0-9_가-힣]*".join(map(re.escape, tokens)) + r"(?![a-z0-9_])"
                changed = re.sub(pattern, marker, changed, flags=re.I)
        if changed != remaining:
            selected.append(label)
            remaining = changed
    return remaining, tuple(selected)


def derived_request(masked, labels):
    growth, share = GROWTH.search(masked), SHARE.search(GROWTH.sub(" ", masked))
    if not (growth or share) or not TEMPORAL.search(GROWTH.sub(" ", SHARE.sub(" ", masked))):
        return None, None
    if growth and share:
        return None, "비중의 증감률처럼 여러 파생 계산을 겹치지 않았습니다. 비중 추이 또는 원본 지표의 증감률을 지정해 주세요."
    if growth:
        if len(labels) != 1:
            return None, "증감률을 계산할 원본 지표를 하나로 지정해 주세요. 여러 원본 중 임의로 선택하지 않았습니다."
        bases = [name for name, pattern in (("year", YOY), ("month", MOM), ("previous", PREVIOUS)) if pattern.search(masked)]
        if len(bases) > 1:
            return None, "증감률의 비교 기준이 여러 개입니다. 전년 동기·전월·이전 관측값 중 하나를 지정해 주세요."
        return DerivedRequest("growth", labels, bases[0] if bases else "previous", "감소율" in masked), None
    if len(labels) != 2:
        return None, "비중·비율의 분자와 분모를 원본 항목명으로 각각 지정해 주세요. 전체나 합계를 임의로 만들지 않았습니다."
    orientation = _ratio_orientation(masked)
    if orientation is None:
        return None, "비율의 분자와 분모 순서를 확정하지 못했습니다. '분모 중 분자의 비중' 또는 '분자 / 분모 비율'로 지정해 주세요."
    component = bool(re.search(r"비중|점유율|\b(?:share|proportion)\b", masked, re.I))
    return DerivedRequest("share", tuple(labels[number] for number in orientation), component=component), None


def _ratio_orientation(masked):
    marker = r"__metric([01])__"
    patterns = [(marker + r"\s*/\s*" + marker, False),
                (marker + r"\s*(?:의\s*)?(?:중|대비)\s*" + marker, True),
                (marker + r"\s*(?:의\s*)?(?:as\s+a\s+share\s+of|to|of)\s*" + marker, False),
                (marker + r"\s*(?:의\s*)?" + marker + r"\s*대비", False)]
    found = set()
    for pattern, reverse in patterns:
        for match in re.finditer(pattern, masked, re.I):
            pair = tuple(map(int, match.groups()))
            found.add(pair[::-1] if reverse else pair)
    return next(iter(found)) if len(found) == 1 and len(set(next(iter(found)))) == 2 else None


def calculation_question(question):
    """Remove only supported mathematical syntax; leave unknown filters intact."""
    for pattern in (YOY, MOM, PREVIOUS, GROWTH, SHARE):
        question = pattern.sub(" ", question)
    question = re.sub(r"\bas\s+a\s+\b|\b(?:of|to)\b|(?<![가-힣])(?:중에서|중|대비)(?![가-힣])|/|(?:늘었|줄었|변했)(?:어|나요|는지)?", " ", question, flags=re.I)
    return question + " 추이"


def source_question(masked, labels):
    question = calculation_question(masked)
    for number, label in enumerate(labels):
        question = question.replace(f"__metric{number}__", label)
    return question
