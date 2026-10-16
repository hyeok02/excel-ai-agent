"""Resolve only source-defined, single rectangular references."""
import re

from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_structured_references import structured_reference

_ADDRESS = re.compile(r"\$?[A-Z]{1,3}\$?[1-9]\d*(?::\$?[A-Z]{1,3}\$?[1-9]\d*)?", re.I)
_ABSOLUTE = re.compile(r"\$[A-Z]{1,3}\$[1-9]\d*(?::\$[A-Z]{1,3}\$[1-9]\d*)?", re.I)


def bind_reference(raw: str, sheet: str, resolver) -> str:
    qualifier, token = split_reference(raw)
    if _ADDRESS.fullmatch(token):
        return raw
    metadata = resolver.index.reference_metadata
    if metadata.unavailable:
        raise FormulaUnavailable(metadata.unavailable, (raw,))
    if "[" in raw:
        if "!" in raw[:raw.index("[")]:
            raise FormulaUnavailable("external_data", (raw,))
        return structured_reference(raw, sheet, resolver)
    scope = canonical_sheet(qualifier or sheet, resolver.sheets)
    matches = [item for item in metadata.names if item.name.casefold() == token.casefold()]
    local = [item for item in matches if item.scope == scope]
    candidates = local or ([item for item in matches if item.scope is None] if qualifier is None else [])
    if candidates:
        if len(candidates) != 1 or any(table.name.casefold() == token.casefold() for table in metadata.tables):
            raise FormulaUnavailable("unsupported_reference", (raw,))
        target = candidates[0].target.removeprefix("=")
        target_sheet, address = split_reference(target)
        if "[" in target or "|" in target:
            raise FormulaUnavailable("external_data", (raw,))
        if len(target) > resolver.limits.max_formula_length or not target_sheet or not _ABSOLUTE.fullmatch(address):
            raise FormulaUnavailable("unsupported_reference", (raw,))
        bound_sheet = canonical_sheet(target_sheet, metadata.allowed_sheets)
        return quote_sheet(bound_sheet) + "!" + address
    if qualifier is None and any(table.name.casefold() == token.casefold() for table in metadata.tables):
        return structured_reference(token, sheet, resolver)
    raise FormulaUnavailable("unsupported_reference", (raw,))


def split_reference(raw):
    if "!" not in raw:
        return None, raw
    qualifier, token = raw.rsplit("!", 1)
    if qualifier.startswith("'") and qualifier.endswith("'"):
        qualifier = qualifier[1:-1].replace("''", "'")
    return qualifier, token


def canonical_sheet(name, available):
    matches = [sheet for sheet in available if sheet.casefold() == name.casefold()]
    if len(matches) != 1:
        raise FormulaUnavailable("missing_reference", (name,))
    return matches[0]


def quote_sheet(sheet):
    return "'" + sheet.replace("'", "''") + "'"
