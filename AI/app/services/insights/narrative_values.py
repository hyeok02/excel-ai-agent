"""Formatting and source-scoped identity/units for deterministic narratives."""
import math
import re
from datetime import datetime

from app.services.insights.fact_trends import is_identity_row
from app.services.insights.glossary import readable
from app.services.insights.models import WorkbookInsight


def number(value):
    parsed = float(value)
    if parsed.is_integer() or abs(parsed) >= 1000:
        return f"{parsed:,.0f}"
    return f"{parsed:,.2f}".rstrip("0").rstrip(".")


AMOUNT_NOTE = re.compile(
    r"\bin\s+\$?\s*(millions|billions|thousands)\b"
    r"|단위\s*[:：(]?\s*(백만|십억|천)",
    re.I,
)
AMOUNT_TEXT = {"millions": "백만 달러", "billions": "십억 달러",
               "thousands": "천 달러", "백만": "백만", "십억": "십억", "천": "천"}
PER_SHARE = re.compile(r"per\s+share|\beps\b|주당", re.I)


def amount_unit(sheet):
    """Tables state their money unit once, in a note above the numbers."""
    name = str(sheet.get("name", ""))
    for region in sheet.get("business_facts", {}).get("table_regions", []):
        for row in region.get("rows", []):
            for cell in row:
                found = AMOUNT_NOTE.search(str(cell.get("value", "")))
                if found and cell.get("cell"):
                    key = (found.group(1) or found.group(2)).casefold()
                    text = AMOUNT_TEXT.get(key, "")
                    if text:
                        return text, [reference(name, cell["cell"])]
    return "", []


def subject_particle(text):
    """Pick 이/가 from the last character so the sentence reads naturally."""
    last = str(text).strip()[-1:]
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
    return "", []


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
