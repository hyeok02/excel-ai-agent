"""Bind a composed bilingual phrase only to a fully named stored ratio field.

These are reusable vocabulary atoms, never a dataset header alias. Every
meaningful source atom and its part/whole order must agree with the phrase;
unknown qualifiers, currency measures and partially named fields do not match.
"""
import re

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.tabular_catalog import build_query_tables

_WORDS = {
    "ratio": ("percentage", "percent", "proportion", "share", "ratio", "비중", "비율", "점유율", "백분율", "%"),
    "sales": ("sales", "revenue", "판매", "매출"),
    "internet": ("internet", "인터넷"),
    "online": ("online", "온라인"),
    "retail": ("retail", "소매"),
    "wholesale": ("wholesale", "도매"),
    "export": ("exports", "export", "수출"),
    "import": ("imports", "import", "수입"),
    "domestic": ("domestic", "국내"),
    "foreign": ("foreign", "해외"),
    "services": ("services", "service", "서비스"),
    "goods": ("goods", "상품"),
    "manufacturing": ("manufacturing", "제조"),
    "employees": ("employees", "headcount", "직원", "인원"),
    "orders": ("orders", "주문"),
    "cost": ("cost", "costs", "비용"),
    "assets": ("assets", "asset", "자산"),
}
_ATOM = {word.casefold(): concept for concept, words in _WORDS.items() for word in words}
_NEUTRAL = {"as", "a", "an", "of", "the", "total", "overall", "in"}
_WORD_PATTERN = re.compile("|".join(
    (r"(?<![a-z])" + re.escape(word) + r"(?![a-z])") if word.isascii() and word.isalpha() else re.escape(word)
    for word in sorted(_ATOM, key=len, reverse=True)), re.I)


def stored_ratio_question(question, summary):
    """Return a source-header spelling only for a unique, fully covered phrase."""
    if not re.search(r"비중|비율|점유율|백분율", question):
        return question
    tables = build_query_tables(summary)
    named = mentioned_sources((table.sheet_name for table in tables), question)
    tables = [table for table in tables if not named or table.sheet_name in named]
    matches = {}
    for table in tables:
        for column in table.columns:
            if column.id in table.hidden_columns or not ("%" in column.header or any(
                    parse_number_format(value).percent for value in column.number_formats)):
                continue
            atoms = _label_atoms(column.header)
            if atoms is None or "ratio" not in atoms or len(atoms) < 2:
                continue
            for start, end, found in _phrases(question):
                if found == atoms and re.search(r"[가-힣]", question[start:end]):
                    matches.setdefault((start, end), set()).add(column.header)
    # Do not silently choose one of differently qualified source metrics.
    if len(matches) != 1:
        return question
    (start, end), labels = next(iter(matches.items()))
    if len(labels) != 1:
        return question
    return question[:start] + next(iter(labels)) + question[end:]


def _label_atoms(label):
    tokens = re.findall(r"[a-z]+|[가-힣]+|\d+|%", label.casefold())
    if any(token not in _ATOM and token not in _NEUTRAL for token in tokens):
        return None
    relation = re.fullmatch(r"(.+?)\s+(?:as\s+a\s+)?(?:percentage|share|ratio|proportion)\s+of\s+(.+?)\s*(?:\(%\))?", label, re.I)
    if relation:
        numerator, denominator = [_plain_atoms(part) for part in relation.groups()]
        shared = set(numerator) & set(denominator) & {"sales", "cost", "employees", "orders", "assets"}
        if len(shared) != 1:
            return None
        measure = next(iter(shared))
        return tuple([atom for atom in numerator if atom not in {measure, "ratio"}]
                     + [atom for atom in denominator if atom not in {measure, "ratio"}]
                     + [measure, "ratio"])
    return _plain_atoms(label)


def _plain_atoms(label):
    atoms = []
    for token in re.findall(r"[a-z]+|[가-힣]+|%", label.casefold()):
        atom = _ATOM.get(token)
        if atom and (not atoms or atoms[-1] != atom):
            atoms.append(atom)
    return tuple(atoms)


def _phrases(question):
    groups = []
    for match in _WORD_PATTERN.finditer(question):
        if not groups or question[groups[-1][-1].end():match.start()].strip():
            groups.append([])
        groups[-1].append(match)
    for group in groups:
        start, end = group[0].start(), group[-1].end()
        before, after = question[:start], question[end:]
        if before and re.search(r"[a-z가-힣]$", before, re.I):
            continue
        if after and re.match(r"[a-z가-힣]", after, re.I) and not re.match(
                r"(?:은|는|을|를|이|가|의|과|와|도|만)(?=$|\s|[^a-z가-힣])", after, re.I):
            continue
        yield start, end, tuple(_ATOM[match.group().casefold()] for match in group)
