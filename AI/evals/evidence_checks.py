"""Source-coordinate coverage checks, without iterating potentially huge grids."""
import re

from openpyxl.utils import range_boundaries


def source_ranges(evidence):
    ranges = []
    if not isinstance(evidence, list):
        return ranges
    for item in evidence:
        if not isinstance(item, dict):
            continue
        sheet = item.get("sheet_name")
        bounds = _bounds(item.get("reference"))
        if isinstance(sheet, str) and sheet and bounds is not None:
            ranges.append((sheet, bounds))
    return ranges


def evidence_errors(targets, evidence):
    """Every oracle cell must be covered by the union of correct-sheet citations."""
    ranges, errors = source_ranges(evidence), []
    for target in targets or []:
        parsed = _target(target)
        if parsed is None:
            errors.append(f"Invalid source coverage target: {target}")
            continue
        sheet, bounds = parsed
        if not _covered(bounds, [box for name, box in ranges if name == sheet]):
            errors.append(f"Missing source coverage: {target}")
    return errors


def _target(target):
    if not isinstance(target, str):
        return None
    sheet, separator, reference = target.rpartition("!")
    if not separator or not sheet:
        return None
    if sheet.startswith("'"):
        if not sheet.endswith("'") or not re.fullmatch(r"'(?:[^']|'')+'", sheet):
            return None
        sheet = sheet[1:-1].replace("''", "'")
    bounds = _bounds(reference)
    return (sheet, bounds) if bounds is not None else None


def _bounds(reference):
    if not isinstance(reference, str):
        return None
    reference = reference.strip().replace("$", "").upper()
    if not re.fullmatch(r"[A-Z]{1,3}[1-9]\d*(?::[A-Z]{1,3}[1-9]\d*)?", reference):
        return None
    try:
        left, top, right, bottom = range_boundaries(reference)
    except (ValueError, TypeError):
        return None
    if not (1 <= left <= right <= 16384 and 1 <= top <= bottom <= 1048576):
        return None
    return left, top, right, bottom


def _covered(target, ranges):
    left, top, right, bottom = target
    clipped = [(max(left, a), max(top, b), min(right, c), min(bottom, d))
               for a, b, c, d in ranges if a <= right and c >= left and b <= bottom and d >= top]
    edges = sorted({left, right + 1, *(a for a, _, _, _ in clipped),
                    *(c + 1 for _, _, c, _ in clipped)})
    for edge in edges[:-1]:
        cursor = top
        for start, end in sorted((b, d) for a, b, c, d in clipped if a <= edge <= c):
            if start > cursor:
                return False
            cursor = max(cursor, end + 1)
        if cursor <= bottom:
            return False
    return True
