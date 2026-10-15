"""Reject rewrites that lose explicit constraints or invent source labels."""
import re

from app.agent.query.references import extract_references

CONTEXT_CUE = re.compile(
    r"그\s+|그(?:중|거|것|건|걸|게|럼|래|렇|쪽|대로|때|항목|값|표|둘)|"
    r"(?:이|저|위|해당|앞선|방금|이전)\s*(?:항목|값|표|결과|내용|둘|질문|인사이트)|"
    r"(?:둘|두\s*개|나머지|전자는|후자는)|"
    r"\b(?:those|these|them|it|both|former|latter|same|among|then)\b", re.I,
)
_NEGATION = re.compile(r"아닌|아니|않|없는|제외|말고|\b(?:not|except|excluding|without)\b", re.I)
_OPERATIONS = (
    ("평균", "average", "mean"), ("합계", "총합", "sum", "total"),
    ("최대", "가장 큰", "maximum", "highest"), ("최소", "가장 작은", "minimum", "lowest"),
    ("차이", "달라", "다른", "비교", "compare", "difference"),
)
_REFERENTS = {
    "그", "이", "저", "그중", "이중", "그럼", "그러면", "그렇다면", "여기서", "거기서",
    "그거", "이거", "저거", "그것", "이것", "저것", "둘", "두", "것", "해당",
    "그건", "그걸", "그게", "이건", "이걸", "이게", "저건", "저걸", "저게",
    "위", "앞선", "방금", "이전", "나머지", "그쪽", "거기", "여기", "그때",
    "those", "these", "them", "it", "both", "former", "latter", "same", "among", "then",
}
_PARTICLES = ("으로", "에서", "까지", "부터", "보다", "에게", "은", "는", "이", "가",
              "을", "를", "의", "에", "도", "만", "과", "와")


def subject_only_followup(question: str, index) -> bool:
    """A source label alone does not say which previously requested value to use."""
    core = re.sub(r"^(?:그럼|그러면|그렇다면|그런데|그리고)\s*|"
                  r"^(?:what about|how about|and|then)\s+", "", question.strip(), flags=re.I)
    core = core.rstrip(" ?？.!。 ").casefold()
    labels = {str(cell.value).strip().casefold() for row in index.rows for cell in row.cells
              if isinstance(cell.value, str) and len(cell.value.strip()) >= 2}
    return any(core in {label, label + "은", label + "는", label + "도"} for label in labels)


def _content_preserved(original, rewritten):
    original = re.sub(r"(?:그|이|저|해당|위|앞선|방금|이전)\s*(?:항목|값|표|결과|내용|둘|질문)", " ", original)
    for word in re.findall(r"[a-z][a-z0-9_-]*|[가-힣]+", original.casefold()):
        stem = word
        for suffix in _PARTICLES:
            if word.endswith(suffix) and len(word) > len(suffix):
                stem = word[:-len(suffix)]
                break
        if word in _REFERENTS or stem in _REFERENTS or word in _PARTICLES:
            continue
        if word not in rewritten and stem not in rewritten:
            return False
    return True


def resolution_is_safe(original: str, draft, context: list[dict]) -> bool:
    if not draft.question or not draft.context_ids:
        return False
    entries = {entry["id"]: entry for entry in context}
    if any(key not in entries for key in draft.context_ids):
        return False
    rewritten = draft.question.casefold()
    selected = [entries[key] for key in draft.context_ids]
    # Preserve explicit IDs, periods and filter numbers exactly; never "correct"
    # a missing requested ID to one found in a previous answer.
    numbers = re.findall(r"\d+(?:[.,]\d+)*", original)
    rewritten_numbers = re.findall(r"\d+(?:[.,]\d+)*", rewritten)
    if any(number not in rewritten_numbers for number in numbers):
        return False
    for pattern in (r"#\s*\d+", r"\d+(?:[.,]\d+)*\s*%", r"\d+(?:[.,]\d+)*(?:천|만|억|조)"):
        expected = {re.sub(r"\s+", "", value) for value in re.findall(pattern, original)}
        actual = {re.sub(r"\s+", "", value) for value in re.findall(pattern, rewritten)}
        if not expected <= actual:
            return False
    if not _content_preserved(original, rewritten):
        return False
    if any(ref not in extract_references(rewritten) for ref in extract_references(original)):
        return False
    if _NEGATION.search(original) and not _NEGATION.search(rewritten):
        return False
    folded = original.casefold()
    for group in _OPERATIONS:
        if any(word in folded for word in group) and not any(word in rewritten for word in group):
            return False
    for quoted in re.findall(r"[\"'‘“]([^\"'’”]+)[\"'’”]", original):
        if quoted.casefold() not in rewritten:
            return False
    source_labels = [str(cell["value"]).strip() for entry in selected
                     for cell in entry["source_cells"] if isinstance(cell["value"], str)]
    # Already explicit source labels cannot be replaced with another label.
    for label in source_labels:
        if len(label) >= 2 and label.casefold() in folded and label.casefold() not in rewritten:
            return False
    # At least one actual source label or address must anchor the resolved referent.
    anchored = any(len(label) >= 2 and label.casefold() in rewritten for label in source_labels)
    return anchored or any(ref in extract_references(rewritten) for entry in selected
                           for cell in entry["source_cells"]
                           for ref in extract_references(cell["reference"]))
