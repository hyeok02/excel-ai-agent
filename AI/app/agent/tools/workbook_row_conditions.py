"""질문이 가리키는 열과 조건을 읽는다."""
from collections import Counter, defaultdict
from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_headers import HeaderContext, header_for
from app.services.insights.facts.flag_columns import mark_of
from app.agent.tools.workbook_label_columns import (
    column_of,
    header_reference,
    is_hangul,
    labelled_column,
)

NEGATIVE_MARKS = {"x"}
POSITIVE_MARKS = {"o", "v"}
# 조사가 붙어도 걸리도록 어간만 둔다.
NEGATIVE_STEMS = ("안", "못", "없", "불", "미", "아닌", "아직")
POSITIVE_STEMS = ("된", "됨", "완료", "있", "정상", "끝난")
MIN_TERM = 2
MAX_PARTICLE = 2


def requested_condition(
    question: str, rows: list[IndexedRow], headers: HeaderContext
):
    """(시트, 열, 머리글, 머리글 셀, 극성) 또는 질문이 분명하지 않으면 None."""
    best = matched_column(question, rows, headers)
    if best is None:
        return None
    sheet_name, column, header, reference = best
    polarity = _polarity(question, header)
    if polarity is None:
        return None
    return sheet_name, column, header, reference, polarity


def matched_column(question: str, rows: list[IndexedRow], headers: HeaderContext):
    """
    질문에 이름이 나온 열. 머리글과 가장 길게 겹치는 쪽을 고른다.

    셀마다 따로 보면, 머리글을 잘못 물려받은 몇 줄이 표 전체를 대표해 버린다.
    실제로 'CVD #1 IP가 뭐야?'가 '장비'가 아니라 'CVD #13' 열로 갔다. 열마다
    가장 많은 줄이 쓰는 머리글 하나로 추려 두고 견준다.
    """
    found = matched_columns(question, rows, headers)
    return found[0] if found else None


def matched_columns(question: str, rows: list[IndexedRow], headers: HeaderContext):
    """겹치는 정도가 큰 순서로 후보 열을 모두 돌려준다.

    한 시트만 보면 가장 잘 맞는 열 하나로 충분하지만, 여러 시트를 함께 보면
    엉뚱한 시트의 열이 1위를 차지하고 거기서 막혀 버린다. 부르는 쪽이 차례로
    시도할 수 있게 순서대로 내놓는다.
    """
    normalized = question.casefold()
    ranked = []
    for (sheet_name, column), header in _column_headers(rows, headers).items():
        overlap = _overlap(normalized, header.casefold())
        if overlap >= MIN_TERM:
            ranked.append((overlap, sheet_name, column, header))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    found = []
    for _, sheet_name, column, header in ranked:
        reference = header_reference(rows, headers, sheet_name, column, header)
        if reference:
            found.append((sheet_name, column, header, reference))
    return found


def _column_headers(rows, headers) -> dict[tuple[str, str], str]:
    """열마다 가장 많은 줄이 쓰는 머리글."""
    counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in rows:
        for cell in row.cells:
            header = header_for(headers, row.sheet_name, row.row_number, cell.address)
            if header:
                counts[(row.sheet_name, column_of(cell.address))][header] += 1
    return {key: found.most_common(1)[0][0] for key, found in counts.items()}


def _overlap(question: str, header: str) -> int:
    """머리글의 낱말 중 질문에 그대로 나오는 글자 수."""
    return sum(
        len(word) for word in header.replace("(", " ").replace(",", " ").split()
        if len(word) >= MIN_TERM and word in question
    )


def _polarity(question: str, header: str) -> str | None:
    """
    머리글에 쓰인 말을 걷어낸 나머지에서 긍정·부정을 읽는다.

    '네트워크 안정'이라는 머리글을 그대로 두고 보면 '안정된'의 '안'이 부정으로
    읽힌다. 머리글의 낱말을 지우고 남은 자리만 봐야 '불안정한'과 '안정된'이
    갈린다.
    """
    residue = question.casefold()
    for word in header.casefold().replace("(", " ").replace(",", " ").split():
        if len(word) >= MIN_TERM:
            residue = residue.replace(word, " ")
    if marked := _mark_polarity(residue):
        return marked
    if any(stem in residue for stem in NEGATIVE_STEMS):
        return "negative"
    if any(stem in residue for stem in POSITIVE_STEMS):
        return "positive"
    return None


def _mark_polarity(residue: str) -> str | None:
    """질문이 표시를 그대로 부르는 경우. "'네트워크 안정'이 x인 장비"가 그렇다.

    표에 적힌 x·o를 질문에 그대로 쓰는 사람이 많은데, 어간만 보면 아무 극성도
    읽히지 않아 목록 답변이 꺼졌다. 낱말이 표시 한 글자로 시작하고 뒤에 조사만
    붙었을 때로 한정한다. 'ok'나 'vs'가 긍정으로 읽히면 안 된다.
    """
    for word in residue.split():
        token = word.strip(".,:;?!()'\"‘’“”")
        if not token or token[0].isdigit():
            continue
        suffix = token[1:]
        if len(suffix) > MAX_PARTICLE or not all(is_hangul(ch) for ch in suffix):
            continue
        if (mark := mark_of(token)) in NEGATIVE_MARKS:
            return "negative"
        if mark in POSITIVE_MARKS:
            return "positive"
    return None
