"""Korean display names for source labels, from the workbook's own readings.

This layer never selects a measure or invents a domain from numeric data. Each label is
shown by the reading prepared for its workbook (see label_translator), else by the general
glossary, else as written; original labels always stay in the evidence.
"""
import calendar
import re

from app.services.insights.display.glossary import translate
from app.services.insights.display.label_translator import counter, reading


def source_label(value, context=""):
    """The workbook's own reading of a label, part by part; unknown parts keep their source text.

    ``context`` is accepted for callers that pass a sheet or section; readings never depend on it.
    """
    text = " ".join(str(value or "").split())
    if not text or re.search(r"[가-힣]", text):
        return text
    # Hierarchical headings can repeat the exact same total marker. Keep the
    # parent's scope and every other qualifier; remove only that duplicate.
    text = re.sub(r"(\btotal)\s*·\s*total$", r"\1", text, flags=re.I)
    return " · ".join(dict.fromkeys(_part(part.strip()) for part in text.split(" · ")))


def _part(text):
    # Exact financial terms retain the general glossary, except 'Sales': a
    # category/role label cannot acquire the meaning of a revenue measure.
    found = reading(text) or (translate(text) if text.casefold() != "sales" else "")
    return found or _dates(text)


def source_unit(value):
    text = " ".join(str(value or "").split())
    return reading(text) or text


def source_caption(value):
    """A table caption without its numbering, read as a whole; unread, its dates are still written in Korean."""
    text = " ".join(str(value or "").split())
    text = re.sub(r"^(?:table|indicator)\s+[A-Za-z]*\d+(?:\.\d+)*(?:\.?[A-Za-z])?\s*[.:–-]?\s*", "", text, flags=re.I)
    text = re.sub(r"^[A-Z]{2,}\d+\s*:\s*", "", text)
    if not text:
        return ""
    return " ".join(_dates(reading(text) or text).split()).strip(" .")


def caption_measure(value):
    """The one measure a caption names before its qualifiers ("Population estimates: summary for the UK").

    A heading naming several measures, or a rate, change or index, names no single count to attach.
    """
    text = " ".join(str(value or "").split())
    text = re.sub(r"^(?:table|indicator)\s+[A-Za-z]*\d+(?:\.\d+)*(?:\.?[A-Za-z])?\s*[.:–-]?\s*", "", text, flags=re.I)
    text = re.sub(r"^[A-Z]{2,}\d+\s*:\s*", "", text)  # a table code ("MYE4:") names no measure
    heading = re.split(r"\s*[:,(]\s*|\s+(?:by|for|in|of the)\s+", text, maxsplit=1, flags=re.I)[0].strip()
    if (not heading or re.search(r"\b(?:and|versus|vs)\b|[&/]", heading, re.I)
            or re.search(r"growth|change|percent|rate|ratio|density|index|per\s+|share", heading, re.I)):
        return "", ""
    unit = counter(heading)
    if not (measure := reading(heading)):
        return "", ""
    # The count's counter word ("명") only for a caption counting single units, not thousands of them.
    scaled = re.search(r"thousands?|millions?|billions?|hundreds?|천|백만|억", text, re.I)
    return measure, "" if scaled else unit


def _dates(text):
    """Calendar wording written the Korean way; every other word is kept as written."""
    text = re.sub(r"\bmid[- ]((?:19|20|21)\d{2})\s+(?:to|[-–])\s+mid[- ]((?:19|20|21)\d{2})\b",
                  r"\1년 중반~\2년 중반", text, flags=re.I)
    text = re.sub(r"\bmid[- ]((?:19|20|21)\d{2})\b", r"\1년 중반", text, flags=re.I)
    text = re.sub(r"\b((?:19|20|21)\d{2})\s*(?:to|[-–])\s*((?:19|20|21)\d{2})\b", r"\1~\2년", text, flags=re.I)
    for month in range(1, 13):
        text = re.sub(r"\b" + calendar.month_name[month] + r"\s+((?:19|20|21)\d{2})\b",
                      lambda m: f"{m[1]}년 {month}월", text, flags=re.I)
    return text


def section_label(value):
    text = " ".join(str(value or "").split())
    match = re.fullmatch(r"year\s+((?:19|20|21)\d{2})", text, re.I)
    return f"{match[1]}년" if match else source_label(text)


def narrative_scope(sheet, section=""):
    """Skip opaque technical names, not human geographic/entity qualifiers."""
    name = " ".join(str(sheet or "").split())
    if re.fullmatch(r"(?:sheet|table|시트)[ _\d.\-]*", name, re.I):
        name = ""
    name = re.sub(r"^time\s*series\s+", "", name, flags=re.I)
    parts = [source_label(name), section_label(section)]
    return " · ".join(dict.fromkeys(p for p in parts if p))
