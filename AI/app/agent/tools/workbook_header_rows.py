"""어느 줄이 머리글인지 가린다.

글자 비율만 보면 o/x 점검표의 데이터 행이 전부 머리글이 된다. 열마다 값이
고유한지까지 봐도 머리글 바로 아래 첫 데이터 행이 또 머리글로 뽑혔다. 그
행의 값(IP 주소, 장비 이름)도 열 안에서 고유하기 때문이다. 그러면 그 아래
모든 행이 '10.1.7.6'을 머리글로 물려받아, 질문이 가리키는 열을 못 찾는다.

머리글은 아래 데이터보다 머리글다워야 한다. 바로 아래 줄과 견주어 더 낫지
않으면 머리글로 보지 않는다.
"""
import re
from collections import Counter
from dataclasses import dataclass

from app.agent.query.index import IndexedRow

MIN_TEXT_CELLS = 2
MIN_TEXT_SHARE = 0.5
MIN_BLOCK_SHARE = 0.6


@dataclass(frozen=True)
class HeaderScore:
    text_share: float
    unique_share: float
    # 열 이름은 숫자를 거의 담지 않는다. 'IP'와 '10.1.7.6'을 가르는 신호다.
    # 값이 모두 고유한 표에서는 이것만이 머리글과 첫 데이터 행을 가른다.
    digitless_share: float

    def beats(self, other: "HeaderScore | None") -> bool:
        if other is None:
            return True
        return self._ranked() > other._ranked()

    def _ranked(self) -> tuple[float, float, float]:
        return (self.text_share, self.unique_share, self.digitless_share)


def is_header_row(
    row: IndexedRow,
    column_values: dict[tuple[str, str], Counter] | None = None,
    block_width: int = 0,
    below: IndexedRow | None = None,
    scores: dict[tuple[str, int], "HeaderScore | None"] | None = None,
) -> bool:
    if not _shaped_like_a_header(row, block_width):
        return False
    if column_values is None:
        return True
    score = _scored(row, column_values, scores)
    if score is None:
        return False
    if below is None:
        return True
    return score.beats(_scored(below, column_values, scores))


def _scored(row, column_values, scores) -> "HeaderScore | None":
    """같은 줄의 점수를 두 번 계산하지 않는다. 아래 줄과 견주느라 매 줄이
    두 번씩 계산돼 1500행짜리 워크북에서 머리글 계산만 2초가 걸렸다."""
    if scores is None:
        return header_score(row, column_values)
    key = (row.sheet_name, row.row_number)
    if key not in scores:
        scores[key] = header_score(row, column_values)
    return scores[key]


def header_score(
    row: IndexedRow, column_values: dict[tuple[str, str], Counter]
) -> HeaderScore | None:
    text_cells = text_cells_of(row)
    if not text_cells or not row.cells:
        return None
    unique = sum(
        column_values[(row.sheet_name, column_of(cell.address))][cell.value] <= 1
        for cell in text_cells
    )
    digitless = sum(
        not any(character.isdigit() for character in cell.value)
        for cell in text_cells
    )
    return HeaderScore(
        len(text_cells) / len(row.cells),
        unique / len(text_cells),
        digitless / len(text_cells),
    )


def text_cells_of(row: IndexedRow) -> list:
    return [
        cell
        for cell in row.cells
        if isinstance(cell.value, str)
        and cell.value.strip()
        and not _looks_like_date(cell.value)
    ]


def _shaped_like_a_header(row: IndexedRow, block_width: int) -> bool:
    text_cells = text_cells_of(row)
    if len(text_cells) < MIN_TEXT_CELLS:
        return False
    if len(text_cells) / len(row.cells) < MIN_TEXT_SHARE:
        return False
    # 표가 7열을 쓰는데 2칸만 적힌 줄은 머리글이 아니라 띄엄띄엄한 데이터다.
    return not (block_width and len(row.cells) < block_width * MIN_BLOCK_SHARE)


def _looks_like_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", value.strip()))


def column_of(address: str) -> str:
    match = re.match(r"[A-Z]+", address.upper())
    return match.group(0) if match else address
