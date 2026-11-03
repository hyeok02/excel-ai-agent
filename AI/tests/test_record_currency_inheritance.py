"""A linked pivot may supply currency, but cannot change a measure or its scale."""
from copy import deepcopy

import pytest

from app.services.insights.models import WorkbookInsightReport
from app.services.insights.narratives.record_summary import record_summary_report
from app.services.insights.verification.validation_index import workbook_evidence_index
from app.services.insights.verification.validator import _validate_insight, validate_workbook_insights
from tests.test_record_summary_readability import _cell, _rows, _source


def _linked(fmt='$#,##0.00'):
    source = _source()
    source['sheets'].append({
        'name': 'Rollup',
        'pivot_unit_sources': [{
            'source_sheet': 'Records', 'source_range': 'A1:E7', 'source_column': 'C',
            'source_header': 'TotalPrice', 'total_value': 100, 'total_cell': 'D9',
            'number_format': fmt, 'reference': "'Rollup'!D9",
        }],
        'business_facts': {'table_regions': [{'rows': [[_cell('D9', 100, fmt)]]}]},
    })
    return source


def test_source_linked_currency_is_visible_in_total_and_category_but_not_quantity():
    source = _linked()
    items, overview = record_summary_report(source)
    assert '$100' in overview and '$60' in overview
    assert '수량 합계는 21' in overview and '$21' not in overview
    for item in items:
        if item.topic == 'TotalPrice':
            assert "'Rollup'!D9" in item.evidence and '$' in item.fact
        else:
            assert "'Rollup'!D9" not in item.evidence and '$' not in item.fact
    report = validate_workbook_insights(WorkbookInsightReport(overview='', insights=[]), source)
    assert report.validation.overview_validated
    assert report.validation.verified_count == 3
    assert '$100' in report.overview


@pytest.mark.parametrize('field,value', [
    ('source_sheet', 'Other'), ('source_column', 'E'), ('source_header', 'UnitPrice'),
    ('source_range', 'A1:E6'), ('source_range', 'A1:F7'), ('source_range', 'A2:E8'),
    ('total_value', 99), ('total_value', float('nan')), ('reference', ''),
])
def test_unrelated_stale_or_partial_summaries_cannot_supply_currency(field, value):
    source = _linked()
    source['sheets'][1]['pivot_unit_sources'][0][field] = value
    _, overview = record_summary_report(source)
    assert '$' not in overview
    assert '100' in overview  # Normal source totals still answer.


def test_same_total_in_an_unlinked_currency_cell_does_not_supply_currency():
    source = _linked()
    source['sheets'][1]['pivot_unit_sources'] = []
    assert '$' not in record_summary_report(source)[1]


def test_conflicting_linked_currencies_do_not_silently_choose_one():
    source = _linked()
    other = deepcopy(source['sheets'][1]['pivot_unit_sources'][0])
    other.update(number_format='€#,##0.00', reference="'Rollup'!E9")
    source['sheets'][1]['pivot_unit_sources'].append(other)
    overview = record_summary_report(source)[1]
    assert '$' not in overview and '€' not in overview and '100' in overview


@pytest.mark.parametrize('fmt,expected', [
    ('$#,##0,', '$100'), ('[$$-409]#,##0.00', '$100'),
    ('"EUR" #,##0', '100 EUR'), ('£#,##0.00', '£100'),
    ('0%', '100'), ('[$-409]#,##0', '100'),
])
def test_preserves_currency_without_borrowing_summary_scale_or_locale(fmt, expected):
    _, overview = record_summary_report(_linked(fmt))
    assert expected in overview
    assert '0.1' not in overview and '$21' not in overview
    if fmt in {'0%', '[$-409]#,##0'}:
        assert '$' not in overview and '100%' not in overview


def test_explicit_record_currency_is_not_overwritten_by_summary():
    source = _linked()
    for row in _rows(source)[1:]:
        row[2]['number_format'] = '"EUR" #,##0.00'
    overview = record_summary_report(source)[1]
    assert '100 EUR' in overview and '$' not in overview


def test_native_link_works_with_renamed_sheets_and_measure():
    source = _linked()
    source['sheets'][0]['name'] = 'Invoices 2026'
    source['sheets'][1]['name'] = 'Summary A'
    _rows(source)[0][2]['value'] = 'InvoiceAmount'
    source['sheets'][1]['pivot_unit_sources'][0].update(
        source_sheet='Invoices 2026', source_header='InvoiceAmount', reference="'Summary A'!D9")
    assert '$100' in record_summary_report(source)[1]


@pytest.mark.parametrize('failure', ['currency', 'total', 'missing_currency_citation'])
def test_currency_change_or_missing_proof_does_not_receive_verified_badge(failure):
    source = _linked()
    items, _ = record_summary_report(source)
    item = next(item for item in items if item.category == 'metric' and item.topic == 'TotalPrice')
    if failure == 'currency':
        item = item.model_copy(update={'fact': item.fact.replace('$100', '€100')})
    elif failure == 'total':
        item = item.model_copy(update={'fact': item.fact.replace('$100', '$999')})
    else:
        item = item.model_copy(update={'evidence': [ref for ref in item.evidence if ref != "'Rollup'!D9"]})
    assert _validate_insight(item, workbook_evidence_index(source), items) is None
