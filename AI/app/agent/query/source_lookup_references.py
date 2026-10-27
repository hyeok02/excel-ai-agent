"""Narrow source-address requests; no inferred operations or dropped filters."""
import re
from dataclasses import dataclass

from openpyxl.utils import get_column_letter, range_boundaries

from app.agent.query.references import REFERENCE_PATTERN
from app.agent.query.workbook_source_models import SourceReadError

_ADDRESS = re.compile(r"(?<![A-Za-z0-9_])\$?[A-Za-z]{1,3}\$?[1-9]\d*(?::\$?[A-Za-z]{1,3}\$?[1-9]\d*)?(?![A-Za-z0-9_])")
_WORDS = frozenset((
    "셀 범위 값 값은 값을 값이 수치 수치는 수치를 내용 내용은 내용을 원본 저장된 현재 "
    "의 에 은 는 이 가 을 를 알려줘 알려주세요 보여줘 보여주세요 조회 조회해줘 확인 확인해줘 "
    "뭐야 무엇 무엇이야 얼마 얼마야 얼마인지 얼마인가요 얼마입니까 각각 그대로 "
    "계산 결과 결과는 결과를 결과가 "
    "what is are the value values of in cell cells range show tell me please stored contents content read"
).split())


@dataclass(frozen=True)
class SourceRange:
    sheet: str
    address: str
    bounds: tuple[int, int, int, int]

    @property
    def area(self):
        left, top, right, bottom = self.bounds
        return (right - left + 1) * (bottom - top + 1)

    def addresses(self):
        left, top, right, bottom = self.bounds
        return (f"{get_column_letter(column)}{row}" for row in range(top, bottom + 1)
                for column in range(left, right + 1))


def bind_source_reference(reference, source):
    sheet, separator, address = str(reference).strip().rpartition("!")
    if not separator or "[" in sheet or "]" in sheet:
        raise SourceReadError("invalid_reference")
    if sheet.startswith("'") and sheet.endswith("'"):
        sheet = sheet[1:-1].replace("''", "'")
    matches = [name for name in source.authorized_sheets if name.casefold() == sheet.casefold()]
    if len(matches) != 1:
        raise SourceReadError("excluded_sheet")
    address = address.replace("$", "").upper()
    if not re.fullmatch(r"[A-Z]{1,3}[1-9]\d*(?::[A-Z]{1,3}[1-9]\d*)?", address):
        raise SourceReadError("invalid_range")
    left, top, right, bottom = range_boundaries(address)
    if not 1 <= left <= right <= 16384 or not 1 <= top <= bottom <= 1048576:
        raise SourceReadError("invalid_range")
    return SourceRange(matches[0], address, (left, top, right, bottom))


def direct_references(question, source):
    matches = list(REFERENCE_PATTERN.finditer(question))
    if matches:
        references = [match.group() for match in matches]
    elif len(source.authorized_sheets) == 1:
        matches = list(_ADDRESS.finditer(question))
        sheet = next(iter(source.authorized_sheets))
        references = [f"{sheet}!{match.group()}" for match in matches]
    else:
        return None
    if not matches:
        return None
    remaining = question
    for match in reversed(matches):
        remaining = remaining[:match.start()] + " " + remaining[match.end():]
    # Unknown words, numbers, operators, units, filters and business labels keep
    # the question on its normal planning path, never a partial direct answer.
    remaining = re.sub(r"[\s?？!.,，、‘’“”\"'()]+", " ", remaining).strip().casefold()
    if any(not _lookup_word(word) for word in remaining.split()):
        return None
    return [bind_source_reference(reference, source) for reference in dict.fromkeys(references)]


def _lookup_word(word):
    if word in _WORDS:
        return True
    # Korean particles attach to the lookup noun. Match the whole token so a
    # filter, arithmetic operation or different business metric is never erased.
    return bool(re.fullmatch(r"(?:셀|범위|값|수치|내용|원본|결과)(?:의|에|은|는|이|가|을|를)", word))
