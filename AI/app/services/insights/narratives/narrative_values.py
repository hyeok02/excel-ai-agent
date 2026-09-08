"""Formatting and source-scoped identity/units for deterministic narratives."""
import math
import re
from datetime import datetime

from app.services.insights.facts.fact_trends import is_identity_row
from app.services.insights.display.glossary import readable
from app.services.insights.models import WorkbookInsight


def number(value):
    parsed = float(value)
    if parsed.is_integer() or abs(parsed) >= 1000:
        return f"{parsed:,.0f}"
    return f"{parsed:,.2f}".rstrip("0").rstrip(".")


def subject_particle(text):
    """Pick 이/가 from the word the reader says: a gloss in brackets is an aside."""
    spoken = re.sub(r"\s*[(（][^)）]*[)）]\s*$", "", str(text)).strip()
    last = (spoken or str(text).strip())[-1:]
    if not last:
        return "가"
    if "가" <= last <= "힣":
        return "이" if (ord(last) - 0xAC00) % 28 else "가"
    return "가" if last in "aeiouyAEIOUY0123456789" else "이"


def workbook_identity(context):
    """The subject can sit on a sheet other than the one being narrated."""
    for sheet in context.get("sheets", []):
        if not isinstance(sheet, dict):
            continue
        name, refs = identity(sheet)
        if name:
            return name.split(" (")[0].strip(), refs
    from app.services.insights.facts.subject_detection import spanning_subject

    name, refs = spanning_subject(context)
    return (name.split(" (")[0].strip(), refs) if name else ("", [])


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def period(value):
    try:
        date = datetime.fromisoformat(str(value))
        return f"{date.year}년 {date.month}월 {date.day}일"
    except ValueError:
        return " ".join(str(value).split())


def reference(sheet, cell):
    return f"'{str(sheet).replace(chr(39), chr(39) * 2)}'!{cell}"


def insight(title, fact, evidence, category="summary", severity="info"):
    return WorkbookInsight(title=title, fact=fact, category=category, severity=severity,
                           evidence=list(dict.fromkeys(evidence)), confidence=1.0)


def overall(metric):
    return bool(re.search(r"\b(?:total|overall)\b|전체|총합|합계|총\s*인원", metric, re.I))


def metric_name(metric):
    # A display translation of an explicit source header, not a domain guess.
    return readable(metric)


def identity(sheet):
    for record in sheet.get("business_facts", {}).get("selected_records", []):
        values = record.get("values", [])
        labels = " ".join(str(value.get("value", "")) for value in values[:-1])
        explicit = bool(re.search(
            r"(?:분석\s*)?대상|회사|기업|기관|\b(?:company|entity|focus)\b|►", labels, re.I
        ))
        if (explicit and is_identity_row(values) and record.get("location")
                and values[-1].get("cell")):
            return str(values[-1]["value"]).strip(), [str(record["location"])]
    return "", []


def metric_unit(metric, records):
    for record in records:
        for cell in record.get("values", []):
            if cell.get("label") != metric:
                continue
            literals = re.findall(r'"([^"\d]+)"', str(cell.get("number_format", "")))
            if literals:
                return literals[-1].strip()
    if re.search(r"\bemployees?\b|\bheadcount\b|인원|직원\s*수", metric, re.I):
        return "명"
    return ""
