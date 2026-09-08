"""Tell measured quantities from quantities already derived from them.

A growth rate, ratio or share is a second-order figure: comparing two of them
answers "how did the change change", which reads poorly as a headline fact.
Narratives keep such rows, but never let them outrank an absolute measure.
"""
import re

TOTAL_NAME = re.compile(r"\btotal\b|전체|합계|총합", re.I)

DERIVED_NAME = re.compile(
    r"\b(?:growth|cagr|ratio|margin|yield|rate|share|percent(?:age)?|multiple|"
    r"per\s+share|change)\b|[%％]|/"
    r"|증감|증가율|성장률|비율|비중|구성비|점유율|수익률|이익률"
    r"|가동률|불량률|달성률|수율|배수|마진",
    re.I,
)
PERCENT_FORMAT = re.compile(r"[%％]")


def derived_label(text) -> bool:
    """True when the column or row name itself announces a derived figure."""
    return bool(DERIVED_NAME.search(" ".join(str(text or "").split())))


def percent_formatted(cells) -> bool:
    return any(
        PERCENT_FORMAT.search(str(cell.get("number_format", "") or ""))
        for cell in cells
        if isinstance(cell, dict)
    )


def derived_metric(name, cells=()) -> bool:
    return derived_label(name) or percent_formatted(cells)


def magnitude_weight(value) -> float:
    """Rank a change by how much of the workbook it moves, not only by its rate.

    A 21% swing on a 6.03 growth-rate row and a 10% swing on a 648,125 revenue
    row are not comparable; without this the smaller number always wins.
    """
    try:
        size = abs(float(value))
    except (TypeError, ValueError):
        return 0.0
    if size < 1:
        return 0.0
    return len(f"{int(size)}")


def change_score(change):
    """Order changes so an absolute measure always outranks a derived one."""
    metric = str(change.get("metric", ""))
    return (
        not derived_metric(metric),
        bool(TOTAL_NAME.search(metric)),
        magnitude_weight(change.get("latest_value")),
        abs(float(change.get("change_rate_percent", 0))),
    )
