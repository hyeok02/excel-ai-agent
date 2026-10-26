"""Bind horizontal narrative values, units and path to the same complete series."""
import re

from app.services.insights.display.amount_units import PER_SHARE
from app.services.insights.display.display_quality import metric_family
from app.services.insights.display.derived_metrics import derived_metric
from app.services.insights.display.glossary import readable
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.facts.series_scalars import displayed_value, scalar, unit as cell_unit
from app.services.insights.models import WorkbookInsight
from app.services.insights.narratives.narrative_values import number, period, reference
from app.services.insights.narratives.series_path import path_direction
from app.services.insights.narratives.topic_labels import scoped_source_topic

_CATEGORIES = re.compile(r"\b(?:roles?|departments?|countries|regions?)\b|직무|부서|국가|지역", re.I)


def horizontal_insight(sheet, series, owner=("", ()), unit=("", ())):
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
    category = bool(_CATEGORIES.search(scope)) or cell_unit(earliest) == "명"
    metric_text = metric if category else readable(metric)
    subject = f"{readable(scope)}의 {metric_text}" if scope else metric_text
    topic = (subject if category else scoped_source_topic(
        metric, series.get("label_cell"), scope, series.get("scope_cell")))
    money, money_refs = _unit(metric, scope, earliest, unit)
    fact = _change(subject, earliest, latest, old, new, money)
    if len(points) > 2:
        indexes = sorted({0, len(points) // 3, 2 * len(points) // 3, len(points) - 1})
        timeline = " → ".join(f"{period(points[index]['period'])} {number(values[index])}{money}"
                              for index in indexes)
        coverage = "기간별 기록" if len(indexes) == len(points) else "주요 시점의 기록"
        fact += f" {coverage}은 {timeline}입니다. {path_direction(values)}"
    evidence = [series.get("scope_cell"), series.get("label_cell"),
                *(point.get(key) for point in points for key in ("period_cell", "value_cell"))]
    return WorkbookInsight(
        title=f"{subject} 변화", fact=fact, category="change",
        severity="info", evidence=[*owner[1], *money_refs,
                                  *(reference(sheet, cell) for cell in dict.fromkeys(evidence) if cell)],
        confidence=1.0, topic=topic,
    )


def _unit(metric, scope, point, sheet_unit):
    explicit = cell_unit(point)
    if explicit:
        return explicit, []
    if derived_metric(f"{scope} {metric}"):
        return "", []
    family = metric_family(metric)
    if family == "headcount":
        return "명", []
    if PER_SHARE.search(f"{scope} {metric}") or _CATEGORIES.search(scope):
        return "", []
    return sheet_unit if family else ("", [])


def _change(subject, earliest, latest, old, new, unit):
    before, after = (f"{period(point['period'])} {number(value)}{unit}"
                     for point, value in ((earliest, old), (latest, new)))
    if old == new:
        return f"{subject}: {before}과 {after}으로 시작과 마지막 값이 같습니다."
    direction = "감소" if new < old else "증가"
    if unit == "%":
        return f"{subject}: {before}에서 {after}로 {direction}했습니다."
    delta = f"{number(abs(new - old))}{unit}"
    if old:
        delta += f"({abs((new - old) / old * 100):.2f}%)"
    return f"{subject}: {before}에서 {after}로 {delta} {direction}했습니다."
