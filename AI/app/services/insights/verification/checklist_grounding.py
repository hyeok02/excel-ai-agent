"""Checklist assertions need actual status tokens even on the canonical path."""
import re

from app.services.insights.facts.flag_columns import mark_of


def grounded_checklist_source(text, sources):
    checklist_claim = (
        re.search(r"점검한\s*표|아무\s*항목도\s*표시되지", text)
        or re.search(r"기재된\s*[\d,]+건이\s*[^\s]+\s*[\d,]+건", text)
    )
    if not checklist_claim:
        return True
    # Numeric cells, numeric formats and descriptions are not mark evidence.
    # This guard also covers previously generated or cached false checklists;
    # matching a canonical sentence cannot waive this source-type check.
    return any(mark_of(value) is not None for value in sources)
