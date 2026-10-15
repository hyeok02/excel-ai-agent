"""질문이 가리키는 행 하나를 이름으로 찾는다."""
from collections import Counter

from app.agent.tools.workbook_label_columns import column_of, is_hangul

MIN_TOKEN = 2
# 긴 것부터 떼야 '으로'가 '로'로 잘리지 않는다.
PARTICLES = (
    "으로", "에서", "에게", "의", "은", "는", "이", "가",
    "을", "를", "에", "와", "과", "도", "만", "로",
)


def named_row(rows, sheet_name, label_column, question, header_reference):
    """
    질문이 한 행만 가리킬 때 그 행. 둘 이상 걸리면 짚지 않는다.

    'CVD #1'과 'CVD #11'은 'cvd'를 함께 쓴다. 모든 이름이 공유하는 낱말로는
    행을 고를 수 없으므로, 한 행에만 있는 낱말로 가리켰을 때만 인정한다.
    """
    asked = tokens(question)
    candidates = []
    for row in rows:
        if row.sheet_name != sheet_name:
            continue
        for cell in row.cells:
            if column_of(cell.address) != label_column:
                continue
            text = str(cell.value or "").strip()
            if text and cell.reference != header_reference:
                candidates.append((text, tokens(text), (cell, row)))
    shared = Counter(token for _, found, _ in candidates for token in found)
    distinctive = {token for token in asked if shared.get(token) == 1}
    if not distinctive:
        return None
    found = [
        (text, place) for text, names, place in candidates if names & distinctive
    ]
    return found[0] if len(found) == 1 else None


def tokens(text: str) -> set[str]:
    """'CVD #1' 과 'CVD #11' 이 섞이지 않게 낱말 단위로 맞춘다."""
    found = set()
    for word in str(text).split():
        token = word.strip(".,:;?!()").casefold()
        if len(token) < MIN_TOKEN:
            continue
        found.add(token)
        if bare := _without_particle(token):
            found.add(bare)
    return found


def _without_particle(token: str) -> str | None:
    """'#1의'가 가리키는 이름은 '#1'이다.

    조사가 붙은 채로는 표의 이름과 맞지 않아 'CVD #1의 IP가 뭐야?'가 답을 못
    냈다. 한글만으로 된 낱말은 건드리지 않는다. '장비는'에서 '장'을 떼면
    엉뚱한 이름에 걸린다.
    """
    for particle in PARTICLES:
        # 한글 명사 자체가 '이/가'로 끝날 수 있다(장비, 차이). 긴 조사와
        # 목적·주제·소유격 조사는 두 글자 이상의 이름 뒤에서만 안전하게 뗀다.
        if all(is_hangul(character) for character in token) and particle in {"이", "가"}:
            continue
        if token.endswith(particle) and len(token) - len(particle) >= MIN_TOKEN:
            return token[: -len(particle)]
    return None
