"""Conservative source-name normalization; no fuzzy or business-name guesses."""
import re
import unicodedata

from app.services.insights.display.glossary import readable

_UNIT = re.compile(
    r"(?<![a-z])(?:USD|EUR|KRW|JPY|GBP|CAD|AUD|CNY|INR|millions?|billions?|"
    r"thousands?|000|M|B)(?![a-z])|[%$€£₩¥]|백만|십억|(?:천만|만|억|조)원|천|원|명|건", re.I,
)
_PARTICLE = r"(?:에서의|으로의|로의|과의|와의|에서는|에서도|에는|에도|에서|으로|까지|부터|은|는|을|를|이|가|의|과|와|도|만|로|별|에)?"


def normalize_label(value):
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return "".join(character for character in text
                   if character.isalnum() or character in "%$€£₩¥/<>±")


def label_base(value):
    text = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\(([^()]*)\)|\[([^\[\]]*)\]", lambda match:
                  "" if unit_qualifier(match[1] or match[2] or "") else match[0], text).strip()


def unit_qualifier(value):
    if not _UNIT.search(value):
        return False
    remainder = _UNIT.sub(" ", value)
    return not re.sub(r"\bin\b|단위|[\s,:/]+", "", remainder, flags=re.I)


def source_mentioned(source, question):
    """Match complete source phrases, allowing Unicode spacing and punctuation."""
    return bool(_source_matches(source, question))


def source_or_reading_mentioned(source, question):
    """원본 글자 그대로, 또는 용어집이 읽어 주는 이름으로 질문과 맞춰 본다.

    표의 값은 영어('Services')인데 질문은 한국어('서비스')라 글자로는 절대
    맞지 않았다. 그래서 후보 순위가 모든 표에서 0점으로 비겼고, 질문이 무엇이든
    같은 후보 목록이 나왔다.
    """
    if source_mentioned(source, question):
        return True
    reading = readable(source)
    if reading == str(source):
        return False
    korean = reading.split("(")[0].strip()
    return bool(korean) and source_mentioned(korean, question)


def mentioned_sources(sources, question):
    matches = [(source, match.span()) for source in set(sources) for match in _source_matches(source, question)]
    # A label inside one longer source phrase is not a separate selection.
    # Separate mentions ("North and North America") still retain both scopes.
    return {source for source, (start, end) in matches
            if not any(other_start <= start and end <= other_end and (start, end) != (other_start, other_end)
                       for _, (other_start, other_end) in matches)}


def _source_matches(source, question):
    source = unicodedata.normalize("NFKC", str(source)).casefold()
    question = unicodedata.normalize("NFKC", question).casefold()
    tokens = re.findall(r"[^\W_]+|[%$€£₩¥/<>±]", source)
    if not tokens:
        return []
    expression = r"[\s\W_]*".join(re.escape(token) for token in tokens)
    # Korean particles may follow a complete label; English prefixes may not.
    return list(re.finditer(r"(?<![\w])" + expression + _PARTICLE + r"(?![\w])", question))


def resolve_unique_column(value, table):
    exact = {column.id for column in table.columns
             if value == column.id or value == column.header or value == column.display_header}
    if exact:
        return next(iter(exact)) if len(exact) == 1 else None
    normalized = normalize_label(value)
    matches = {column.id for column in table.columns
               if normalized and normalized in {normalize_label(column.header), normalize_label(column.display_header)}}
    if not matches:
        # Only remove a complete source unit annotation, never a year,
        # scenario, partial business metric, or a user-supplied different unit.
        matches = {column.id for column in table.columns
                   if normalized and normalize_label(label_base(column.header)) == normalized}
    return next(iter(matches)) if len(matches) == 1 else None
