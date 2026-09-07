"""Formatting and source-scoped identity/units for deterministic narratives."""
import math
import re
from datetime import datetime

from app.services.insights.fact_trends import is_identity_row
from app.services.insights.models import WorkbookInsight


def number(value):
    parsed = float(value)
    return f"{parsed:,.0f}" if parsed.is_integer() else f"{parsed:,.2f}".rstrip("0").rstrip(".")


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


def insight(title, fact, evidence):
    return WorkbookInsight(title=title, fact=fact, category="summary", severity="info",
                           evidence=list(dict.fromkeys(evidence)), confidence=1.0)


def overall(metric):
    return bool(re.search(r"\b(?:total|overall)\b|전체|총합|합계|총\s*인원", metric, re.I))


def metric_name(metric):
    # This is a display translation of an explicit source header, not a domain guess.
    if metric.casefold().strip() == "total employees":
        return "전체 직원 수"
    return metric


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
