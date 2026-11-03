"""Keep caption notes inside the same vertical and side-by-side table block."""
import re

from app.services.insights.narratives.narrative_values import finite


def _header(populated, left, right):
    relevant = [(col, cell) for col, cell in populated if left - 1 <= col <= right]
    if len(relevant) < 2:
        return False
    values = [cell.get("value") for _, cell in relevant]
    if any(re.fullmatch(r"[-—–.]+|N/?A|N/?M|W|#\w+[!?]?|not available|없음", str(value).strip(), re.I)
           for value in values):
        return False
    if all(isinstance(value, str) and len(value) < 100 for value in values):
        return True
    # A cross-tab's first heading can be any source dimension, not just Year.
    # Consecutive year columns are structural headings even when stored as
    # Excel numbers. A single year-like amount is insufficient evidence.
    periods = values[1:]
    return bool(isinstance(values[0], str) and len(values[0]) < 100 and len(periods) >= 2
                and all(finite(value) and int(value) == value and 1900 <= value <= 2099 for value in periods)
                and len(set(periods)) == len(periods)
                and (periods == sorted(periods) or periods == sorted(periods, reverse=True)))


def _column_window(rows, top, left, right):
    """Keep notes in the same side-by-side header block as numeric evidence."""
    for row in sorted((row for row in rows if row < top), reverse=True):
        populated = sorted(rows[row], key=lambda pair: pair[0])
        if not _header(populated, left, right):
            continue
        groups = []
        for col, _ in populated:
            if not groups or col > groups[-1][-1] + 1:
                groups.append([col])
            else:
                groups[-1].append(col)
        selected = [index for index, group in enumerate(groups)
                    if any(left <= col <= right for col in group)]
        if len(selected) != 1:
            return None
        index = selected[0]
        start = groups[index][0] if index else 1
        end = groups[index + 1][0] if index + 1 < len(groups) else float("inf")
        return start, end
    return 1, float("inf")


def _same_column_block(rows, candidate, top, left, right):
    for row in sorted((row for row in rows if candidate[0] < row < top), reverse=True):
        populated = sorted(rows[row], key=lambda pair: pair[0])
        if not _header(populated, left, right):
            continue
        groups = []
        for col, _ in populated:
            if not groups or col > groups[-1][-1] + 1:
                groups.append([col])
            else:
                groups[-1].append(col)
        selected = [group for group in groups if any(left <= col <= right for col in group)]
        if len(selected) > 1:
            return False
        if selected and any(group[-1] < selected[0][0] for group in groups):
            return candidate[1] >= selected[0][0] - 1
        break
    return True
