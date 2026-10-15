"""Conservative source-name normalization; no fuzzy or business-name guesses."""
import re
import unicodedata

_UNIT = re.compile(
    r"(?:(?:USD|EUR|KRW|JPY|GBP|CAD|AUD|CNY|INR)|[%$€£₩¥]|"
    r"million[s]?|billion[s]?|thousand[s]?|000|M|B|백만|십억|천|원|명|건|단위|in|\s)+", re.I,
)


def normalize_label(value):
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return "".join(character for character in text
                   if character.isalnum() or character in "%$€£₩¥/<>±")


def label_base(value):
    return re.sub(r"\(([^()]*)\)", lambda match: "" if _UNIT.fullmatch(match[1].strip())
                  else match[0], str(value)).strip()


def source_mentioned(source, question):
    """Match complete source phrases, allowing Unicode spacing and punctuation."""
    source = unicodedata.normalize("NFKC", str(source)).casefold()
    question = unicodedata.normalize("NFKC", question).casefold()
    tokens = re.findall(r"[^\W_]+|[%$€£₩¥/<>±]", source)
    if not tokens:
        return False
    expression = r"[\s\W_]*".join(re.escape(token) for token in tokens)
    # Korean particles may follow a complete label; English prefixes may not.
    suffix = (r"(?![a-z0-9_])" if tokens[-1].isascii() else
              r"(?:에서|으로|은|는|을|를|이|가|의|과|와|도|만|로|별)?(?![\w])")
    return bool(re.search(r"(?<![\w])" + expression + suffix, question))


def resolve_unique_column(value, table):
    exact = {column.id for column in table.columns
             if value == column.id or value == column.header}
    if exact:
        return next(iter(exact)) if len(exact) == 1 else None
    normalized = normalize_label(value)
    matches = {column.id for column in table.columns
               if normalized and normalize_label(column.header) == normalized}
    return next(iter(matches)) if len(matches) == 1 else None
