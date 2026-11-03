"""Concentration facts from the same validated additive record population."""
import math
import re
from collections import defaultdict

from app.services.insights.display.record_labels import record_group_label, record_header
from app.services.insights.narratives.narrative_values import insight, number, reference
from app.services.insights.narratives.record_summary_support import _words, _range
from app.services.insights.narratives.record_units import record_value


def append_concentration(sheet, rows, headers, records, keys, measures, key_ref, description,
                         display_names, basis_refs, items, overview):
    _, p, name, cells, values, units, unit_refs = measures[0]
    total = math.fsum(values)
    categories = []
    for q, header_cell in headers.items():
        if q in keys or q == p:
            continue
        labels = [row.get(q, {}).get("value") for row in records]
        if not all(isinstance(v, str) and v.strip() and len(v) <= 60 for v in labels):
            continue
        if not 2 <= len(set(labels)) <= 12 or len(set(labels)) > len(rows) * .6:
            continue
        if set(v.casefold() for v in labels) <= {"y", "n", "yes", "no", "true", "false"}:
            continue
        priority = (0 if re.search(r"category|type|class|group|분류|유형|구분", _words(header_cell["value"]), re.I)
                    else 1 if re.search(r"state|status|region|지역|상태", _words(header_cell["value"]), re.I) else 2)
        categories.append((priority, q, header_cell, labels))
    if categories and total > 0 and all(v >= 0 for v in values):
        _, q, category, labels = min(categories, key=lambda c: c[:2])
        grouped = defaultdict(list)
        for label, value in zip(labels, values):
            grouped[label].append(value)
        ranked = sorted(((math.fsum(v), k) for k, v in grouped.items()), reverse=True)
        top, label = ranked[0]
        winners = [k for v, k in ranked if math.isclose(v, top, rel_tol=1e-12)]
        label_text = ", ".join(f"‘{winner}’" for winner in winners)
        category_label, measure_label = record_group_label(category["value"], headers), display_names[name]
        tied = len(winners) > 1
        fact = (f"{category_label}별로 보면 {label_text}의 {measure_label} 합계가 "
                f"{'각각 ' if tied else ''}{record_value(top, units)}로 {'공동으로 ' if tied else ''}가장 큽니다. "
                f"{'각 항목은 ' if tied else '이 항목은 '}전체 {measure_label}의 "
                f"{number(top / total * 100)}%를 차지합니다.")
        evidence = [reference(sheet, category["cell"]), reference(sheet, headers[p]["cell"]),
                    _range(sheet, [row[q] for row in records]), _range(sheet, cells), key_ref,
                    *basis_refs, *description.evidence, *unit_refs]
        if category_label != record_header(category["value"]):
            # The geographic reading of State needs the neighboring schema
            # just as the numeric statement needs the source value range.
            evidence += [reference(sheet, cell["cell"]) for cell in headers.values()
                         if _words(cell["value"]).casefold() in {"city", "region", "country", "location"}]
            evidence = list(dict.fromkeys(evidence))
        items.append(insight(f"{category_label}별 {measure_label} 비중", fact, evidence, "summary", topic=name))
        overview += f" {fact}"
    return items, overview
