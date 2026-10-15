"""Normalize question grammar, never source subjects, numbers or filter predicates."""
import re

LEADING_DISCOURSE = re.compile(r"^(?:그럼|그러면|그렇다면|그런데|그리고)\s*|"
                               r"^(?:then|and)\s+", re.I)
_REQUEST_WORDS = frozenset({
    "알려줘", "알려주세요", "보여줘", "보여주세요", "말해줘", "말해주세요", "줘", "주세요",
    "얼마", "얼마야", "얼마인지", "몇", "몇이야", "명이야", "건이야", "개야", "곳이야",
    "뭐야", "무엇", "어떻게", "인지", "있어", "있나요", "해줘", "해주세요",
    "시트", "표", "범위", "기준", "기준으로", "선택할게",
    "what", "how", "many", "much", "is", "are", "the", "a", "an", "please", "show", "tell", "me",
})
_PARTICLES = ("으로", "에서", "까지", "부터", "보다", "에게", "은", "는", "이", "가",
              "을", "를", "의", "에", "도", "만", "과", "와")


def standalone_wording(question: str) -> str:
    return LEADING_DISCOURSE.sub("", question.strip())


def contains_content_word(word: str, text: str) -> bool:
    if re.fullmatch(r"[a-z][a-z0-9_-]*", word):
        return bool(re.search(r"(?<![a-z0-9_-])" + re.escape(word) + r"(?![a-z0-9_-])", text))
    return word in text


def scope_only_followup(question: str, index) -> bool:
    """An existing sheet selection supplies scope, not a new requested metric."""
    return selected_scope_sheet(question, index) is not None


def selected_scope_sheet(question: str, index) -> str | None:
    """Only a unique, existing sheet plus request grammar is a scope selection."""
    core = standalone_wording(question).casefold()
    matches = []
    for sheet in {row.sheet_name for row in index.rows}:
        if sheet.casefold() not in core:
            continue
        remaining = core.replace(sheet.casefold(), " ")
        remaining = re.sub(r"['\"‘’“”?!.,]", " ", remaining)
        if not content_words(remaining) and not re.search(r"\d|[#%<>!=]", remaining):
            matches.append(sheet)
    return matches[0] if len(matches) == 1 else None


def content_words(question: str) -> set[str]:
    """Keep lexical content; remove only interrogative/polite grammar and particles."""
    words = set()
    for word in re.findall(r"[a-z][a-z0-9_-]*|[가-힣]+", question.casefold()):
        if word in _REQUEST_WORDS or word in _PARTICLES:
            continue
        stem = word
        for suffix in _PARTICLES:
            if word.endswith(suffix) and len(word) > len(suffix):
                stem = word[:-len(suffix)]
                break
        if stem in _REQUEST_WORDS:
            continue
        words.add(stem)
    return words
