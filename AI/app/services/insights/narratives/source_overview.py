"""Compact complete source-generated conclusions without slicing facts or units."""
import re


def compact_facts(items, limit=3, max_chars=440):
    """An overview shows conclusions; full point-by-point paths stay on cards.

    Use complete source-generated sentences, not character truncation or a new
    model call. Recent reversals stay beside the full-period change so a long
    decline is never rewritten as continuous decline, and a latest change on a
    long series keeps its whole-period change so 1999~2023 is not summarized
    as 2022→2023 alone.
    """
    parts, budget = [], []
    for item in items[:limit]:
        sentences = re.split(r"(?<=다\.)\s+", item.fact.strip())
        if not sentences:
            continue
        first = sentences[0]
        # Split complete Korean narrative sentences, never decimal points or
        # abbreviations inside a source's company/category name.
        recent = next((s for s in sentences if s.startswith("최근 구간은 ")), "")
        whole = next((s for s in sentences if s.startswith("전체 기간으로는 ")), "")
        if recent:
            first += " " + recent
        elif len(sentences) > 1 and sentences[1].startswith("이전 기간 대비 "):
            first += " " + sentences[1]
        # Never cut a sentence or its numeric unit to fit a character budget.
        # Additional conclusions remain available in the detailed cards.
        # The whole-period sentence replaces the latest step's percentage and is
        # not counted, so adding it never pushes another conclusion off.
        if parts and len(" ".join([*budget, first])) > max_chars:
            break
        budget.append(first)
        if whole and not recent:
            first = sentences[0] + " " + whole
        parts.append(first)
    # One conclusion per line; the cards keep the full paths.
    return "\n".join(f"· {part}" for part in parts)
