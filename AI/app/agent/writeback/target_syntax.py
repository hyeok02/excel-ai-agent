"""Read explicit destinations independently of model-selected candidate cells."""
import re
from dataclasses import dataclass

ADDRESS = r"\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}"
REFERENCE = re.compile(
    rf"(?<![A-Za-z0-9_$]){ADDRESS}(?:\s*(?::|부터|에서)\s*{ADDRESS}(?:까지)?)?"
    r"(?![A-Za-z0-9_])", re.I,
)
SOURCE = re.compile(r"(?:값을?\s*)?(?:참고|참조|기준|복사해|복사하|에서\s*가져|읽어)", re.I)
EXCLUDED = re.compile(r"말고|아니라|제외|빼고|건드리지|바꾸지|수정하지|not\b|except\b", re.I)
ACTION = re.compile(r"수정|변경|바꿔|바꾸|넣|입력|설정|비우|삭제|지우|줄여|늘려|올려|내려|set|change|clear", re.I)


@dataclass(frozen=True)
class TargetMention:
    reference: str
    start: int
    end: int
    sheet: str | None
    destination: bool = True


def mask_formulas(instruction: str) -> str:
    """Keep offsets, but never authorize formula operands as destinations."""
    chars, position = list(instruction), 0
    while position < len(instruction):
        if instruction[position] != "=":
            position += 1
            continue
        start, depth, quote = position, 0, None
        position += 1
        while position < len(instruction):
            char = instruction[position]
            if quote:
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif depth == 0 and (
                char in ",;\n" or re.match(r"(?:으로|로|을|를|이라고|로써)(?=\s|$|[,;])", instruction[position:])
            ):
                break
            position += 1
        chars[start:position] = " " * (position - start)
    return "".join(chars)


def sheet_mentions(text: str, sheets) -> list[tuple[int, int, str]]:
    found = []
    for name in sorted(sheets, key=len, reverse=True):
        # Excel quoted names escape an apostrophe by doubling it.
        forms = ("'" + name.replace("'", "''") + "'", name)
        for form in forms:
            pattern = rf"(?<![\w]){re.escape(form)}(?![A-Za-z0-9_])"
            for match in re.finditer(pattern, text, re.I):
                if not any(low <= match.start() < high for low, high, _ in found):
                    found.append((*match.span(), name))
    return sorted(found)


def target_mentions(instruction: str, sheets) -> tuple[str, list[TargetMention]]:
    masked = mask_formulas(instruction)
    for literal in re.finditer(r"(['\"])(.*?)\1(?=\s*(?:으로|로|라고|라는))", masked):
        low, high = literal.span()
        masked = masked[:low] + " " * (high - low) + masked[high:]
    sheet_spans = sheet_mentions(masked, sheets)
    matches = [match for match in REFERENCE.finditer(masked)
               if not any(low <= match.start() < high for low, high, _ in sheet_spans)]
    result = []
    for position, match in enumerate(matches):
        tail_end = matches[position + 1].start() if position + 1 < len(matches) else len(masked)
        tail = masked[match.end():tail_end]
        source = SOURCE.search(tail)
        excluded = bool(EXCLUDED.search(tail))
        excluded |= bool(source and not ACTION.search(tail[:source.start()]))
        if position + 1 < len(matches) and not ACTION.search(tail):
            excluded |= bool(re.search(r"(?:에서|의\s*값(?:을)?|값을)\s*$", tail))
        excluded |= bool(re.match(r"\s*[+*/^]", tail) or re.search(r"[+*/^]\s*$", masked[:match.start()]))
        prefix = masked[:match.start()]
        qualified = re.search(r"'((?:[^']|'')+)'\s*!\s*$", prefix)
        preceding = [(high, name) for _, high, name in sheet_spans if high <= match.start()]
        sheet = qualified.group(1).replace("''", "'") if qualified else None
        bare = re.search(r"([^\s,!;]+)\s*!\s*$", prefix)
        if sheet is None and bare:
            sheet = bare.group(1)
            immediate = [(high, name) for high, name in preceding
                         if re.fullmatch(r"\s*!\s*", masked[high:match.start()])]
            if immediate:
                sheet = max(immediate)[1]
        named = re.search(r"(?:'((?:[^']|'')+)'|([^\s]+))\s+시트(?:의|에서|에)?\s*$", prefix)
        if sheet is None and named:
            sheet = (named.group(1) or named.group(2)).replace("''", "'")
            immediate = [(high, name) for high, name in preceding
                         if re.fullmatch(r"\s*시트(?:의|에서|에)?\s*", masked[high:match.start()])]
            if immediate:
                sheet = max(immediate)[1]
        if sheet is None and preceding:
            sheet = max(preceding)[1]
        reference = re.sub(r"\s|\$|까지", "", match.group()).upper()
        reference = reference.replace("부터", ":").replace("에서", ":")
        result.append(TargetMention(reference, match.start(), match.end(), sheet, not excluded))
    return masked, result
