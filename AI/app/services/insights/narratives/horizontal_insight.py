"""Bind horizontal narrative values, units and path to the same complete series."""
import re

from app.services.insights.display.amount_units import PER_SHARE
from app.services.insights.display.display_quality import metric_family
from app.services.insights.display.derived_metrics import derived_metric
from app.services.insights.display.glossary import readable, translate
from app.services.insights.display.source_labels import source_label, source_unit
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.facts.series_scalars import displayed_value, scalar, unit as cell_unit
from app.services.insights.models import WorkbookInsight
from app.services.insights.narratives.change_sentence import change_sentence
from app.services.insights.narratives.narrative_values import number, period, reference
from app.services.insights.narratives.series_path import series_shape
from app.services.insights.narratives.topic_labels import scoped_source_topic

_CATEGORIES = re.compile(r"\b(?:roles?|departments?|countries|regions?)\b|직무|부서|국가|지역", re.I)


def horizontal_insight(sheet, series, owner=("", ()), unit=("", ()), *, caption=("", "", ())):
    points = series.get("observations") or series.get("points", [])
    dates = [date_value(str(point.get("period", ""))) for point in points]
    if (len(points) < 2 or any(date is None for date in dates)
            or len(set(dates)) != len(points)
            or any(not scalar(point.get("value")) for point in points)
            or len({cell_unit(point) for point in points}) != 1):
        return None
    points = sorted(points, key=lambda point: date_value(str(point["period"])))
    if not series.get("observations"):
        points = [points[0], points[-1]]  # Legacy points do not prove a complete intermediate path.
    values = [displayed_value(point) for point in points]
    if len(set(values)) == 1:
        return None
    earliest, latest = points[0], points[-1]
    old, new = values[0], values[-1]
    metric, scope = str(series.get("metric", "")).strip(), str(series.get("scope") or "").strip()
    basis = str(series.get("basis") or "").strip()
    category = bool(_CATEGORIES.search(scope)) or cell_unit(earliest) == "명"
    # A bare Sales label can name a role. Translate it as revenue only when
    # the same series explicitly carries a currency, outside category scopes.
    monetary_sales = metric.casefold() == "sales" and re.search(
        r"\b(?:USD|EUR|KRW|GBP|JPY|INR)\b|[$€₩£¥₹]", cell_unit(earliest), re.I)
    metric_text = metric if category else (
        readable(metric) if translate(metric) and (metric.casefold() != "sales" or monetary_sales)
        else source_label(metric, f"{scope} {basis}"))
    caption_metric, caption_unit, caption_refs = caption
    if caption_metric and caption_metric not in metric_text:
        metric_text = f"{metric_text} {caption_metric}"
    subject = f"{source_label(scope)}의 {metric_text}" if scope else metric_text
    if basis and basis.casefold() != scope.casefold():
        basis_text = source_label(basis)
        if metric.casefold() in {"total", "overall"} and re.search(r"\btotal\b|전체$", basis, re.I):
            subject = f"{basis_text} {caption_metric}".strip()
        else:
            subject = f"{basis_text} · {subject}"
    topic = (subject if category else scoped_source_topic(
        metric, series.get("label_cell"), scope, series.get("scope_cell")))
    if basis:
        topic = f"{basis} · {topic}"
    declared = series.get("declared_unit")
    declared_display = (f" {source_unit(declared['value'])}", [reference(sheet, declared['cell'])]) if declared else None
    money, money_refs = _unit(metric, f"{scope} {basis}", earliest, unit, declared_display)
    if not money and caption_unit and not derived_metric(f"{scope} {basis} {metric}", points):
        money, money_refs = caption_unit, list(caption_refs)
    fact = _change(subject, earliest, latest, old, new, money)
    if len(points) > 2:
        # One line per reading: whole period, latest step, then the series' shape.
        fact += "\n최근 구간은 " + _change(subject, points[-2], latest, values[-2], new, money).split(": ", 1)[-1]
        shape = series_shape([_period(point) for point in points], values,
                             [f"{_display(point, value)}{money}" for point, value in zip(points, values)])
        fact += f"\n{shape}" if shape else ""
    evidence = [series.get("scope_cell"), series.get("label_cell"), *series.get("label_cells", []), series.get("basis_cell"),
                *(point.get(key) for point in points for key in ("period_cell", "value_cell"))]
    return WorkbookInsight(
        title=f"{subject} 변화", fact=fact, category="change",
        severity="info", evidence=[*owner[1], *money_refs, *caption_refs,
                                  *(reference(sheet, cell) for cell in dict.fromkeys(evidence) if cell)],
        confidence=1.0, topic=topic,
    )


def _unit(metric, scope, point, sheet_unit, declared_unit=None):
    explicit = cell_unit(point)
    if explicit:
        return explicit, []
    if derived_metric(f"{scope} {metric}"):
        return "", []
    family = metric_family(metric)
    if family == "headcount":
        return "명", []
    if declared_unit:
        return declared_unit
    if PER_SHARE.search(f"{scope} {metric}") or _CATEGORIES.search(scope):
        return "", []
    return sheet_unit if family else ("", [])


def _change(subject, earliest, latest, old, new, unit):
    before, after = (f"{_period(point)} {_display(point, value)}{unit}"
                     for point, value in ((earliest, old), (latest, new)))
    return f"{subject}: " + change_sentence(before, after, old, new, unit)


def _period(point):
    text = point.get("period_label") or period(point["period"])
    return re.sub(r"^(\d{4}년) 중간$", r"\1 중반", text)


def _display(point, value):
    from app.agent.query.excel_number_formats import number_text, parse_number_format
    spec = parse_number_format(point.get("number_format"))
    return number(value) if spec.mode == "raw" else number_text(value, spec)
