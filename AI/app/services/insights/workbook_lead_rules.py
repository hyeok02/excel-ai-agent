"""Domain-neutral lead sentences selected from validated analysis shapes."""
import re

from app.services.insights.fact_trends import date_value
from app.services.insights.models import ValidatedWorkbookInsightReport
from app.services.insights.narrative_values import workbook_identity
from app.services.insights.reference_matching import matching_references
from app.services.insights.validation_index import extract_references


def structured_lead(
    context: dict[str, object], report: ValidatedWorkbookInsightReport
) -> str:
    return _with_subject(context, (
        _comparison_lead(context, report)
        or _record_lead(report)
        or _trend_lead(report)
        or _event_lead(context, report)
        or _ranked_lead(report)
    ))


def _with_subject(context, lead):
    """Name the subject once it is known, whichever narrative wrote the lead."""
    holder, _ = workbook_identity(context)
    if not lead.startswith("이 파일은 ") or not holder or holder in lead:
        return lead
    return lead.replace("이 파일은 ", f"이 파일은 {holder}의 ", 1)


def _comparison_lead(context, report):
    visible = _visible_references(report)
    for sheet in context.get("sheets", []):
        comparison = sheet.get("business_facts", {}).get("comparable_transactions")
        if not isinstance(comparison, dict) or not comparison.get("metrics"):
            continue
        evidence = [ref for metric in comparison["metrics"]
                    for ref in metric.get("evidence", [])]
        if not any(_same_scope(ref, visible) for ref in evidence):
            continue
        subject = " ".join(str(comparison.get("subject", "")).split())
        if subject:
            return f"이 파일은 {subject} 거래가격을 비슷한 거래들과 비교한 자료입니다."
    return ""


def _record_lead(report):
    """A list of records is described by how many and over what span."""
    counted = [item for item in report.insights if item.title.endswith(" 구성")]
    total = re.search(r"([\d,]+)건 중", counted[0].fact) if counted else None
    if not total:
        return ""
    span = next((found for item in report.insights
                 if (found := re.search(r"기록은 (.+?까지)", item.fact))), None)
    when = f"{span.group(1)}의 " if span else ""
    kind = counted[0].title.rsplit(" 구성", 1)[0]
    return f"이 파일은 {when}‘{kind}’ 기록 {total.group(1)}건을 정리한 목록입니다."


def _trend_lead(report):
    items = [item for item in report.insights if item.category == "trend"
             and not item.title.startswith("주요 항목별")]
    if not items:
        return ""
    if len(items) == 1:
        topic = re.sub(r"\s+변화$", "", " ".join(items[0].title.split()))
        return f"이 파일은 {topic} 변동을 다룹니다."
    topics, owners = [], set()
    for item in items[:3]:
        topic = re.sub(r"\s+변화$", "", " ".join(item.title.split()))
        head, _, tail = topic.rpartition("의 ")
        if head:
            owners.add(head)
        topic = tail or topic
        if topic.casefold() not in {value.casefold() for value in topics}:
            topics.append(topic)
    owner = f"{owners.pop()}의 " if len(owners) == 1 else ""
    return (f"이 파일은 {owner}{'와 '.join(topics[:2])} 등 "
            "주요 수치의 기간별 변동을 다룹니다.")


def _event_lead(context, report):
    visible = _visible_references(report)
    for sheet in context.get("sheets", []):
        records = sheet.get("business_facts", {}).get("selected_records", [])
        for record in records:
            if not _same_scope(str(record.get("location", "")), visible):
                continue
            values = [value.get("value") for value in record.get("values", [])]
            texts = [" ".join(value.split()) for value in values
                     if isinstance(value, str) and not date_value(value)]
            if (any(date_value(value) for value in values)
                    and any(len(value) <= 60 for value in texts)
                    and any(len(value) >= 35 for value in texts)):
                return "이 파일은 주요 사건과 관련 내용을 날짜별로 정리한 자료입니다."
    return ""


def _ranked_lead(report):
    facts = " ".join(item.fact for item in report.insights)
    if "보유 주식 수" in facts and "비중" in facts:
        return "이 파일은 주요 보유자의 주식 보유량과 지분 비중을 정리한 자료입니다."
    if "1위" in facts and "비중" in facts:
        return "이 파일은 항목별 순위와 비중을 정리한 자료입니다."
    return ""


def _visible_references(report):
    return set().union(*(
        extract_references(ref) for item in report.insights for ref in item.evidence
    ))


def _same_scope(value, visible):
    return any(
        matching_references(source, visible)
        or matching_references(target, {source})
        for source in extract_references(value) for target in visible
    )
