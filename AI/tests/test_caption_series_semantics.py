"""A source caption may clarify categories, never relabel another measure."""
import pytest

from app.services.insights.narratives.caption_series import qualified_series_caption
from app.services.insights.narratives.horizontal_trends import horizontal_trend_report


def context(metric, caption='Population estimates: Summary for the UK, 2023-2024', *, basis='', fmt='0', declared=None, geography=False):
    def cell(address, value):
        return {'cell': address, 'value': value}
    rows = [[cell('A1', caption)],
            [cell('A3', 'Region' if geography else 'Metric'), cell('B3', '2023-01-01'), cell('C3', '2024-01-01')],
            [cell('A4', metric), cell('B4', 100), cell('C4', 120)]]
    points = [{'period': f'{year}-01-01', 'period_cell': f'{col}3',
               'value': val, 'value_cell': f'{col}4', 'number_format': fmt}
              for year, col, val in [(2023, 'B', 100), (2024, 'C', 120)]]
    series = {'metric': metric, 'label_cell': 'A4', 'points': points,
              'observations': points, 'basis': basis}
    if declared:
        series['declared_unit'] = {'value': declared, 'cell': 'A2'}
        rows.insert(1, [cell('A2', declared)])
    sheet = {'name': 'Source', 'business_facts': {'horizontal_series': [series], 'table_regions': [{'rows': rows}]}}
    return {'sheets': [sheet]}, sheet, series


@pytest.mark.parametrize('metric', ['Births', 'Average age', 'Population density', 'Area in square kilometres', 'Revenue', 'New unrecognized measure'])
def test_population_caption_does_not_relabel_other_measures(metric):
    source, sheet, series = context(metric)
    assert qualified_series_caption(sheet, series, source['sheets'][0]['business_facts']['table_regions'][0]['rows'][0][0]['value'], []) == ('', '', ())
    items, _ = horizontal_trend_report(source)
    assert items and '인구 추정치' not in items[0].title and '100명' not in items[0].fact


@pytest.mark.parametrize('basis', ['Growth rate', 'Average age', 'Median age', 'Area (km²)', 'Births'])
def test_geographic_row_keeps_its_explicit_parent_measure(basis):
    source, _, _ = context('United Kingdom', basis=basis)
    items, _ = horizontal_trend_report(source)
    assert items and '인구 추정치' not in items[0].title and '100명' not in items[0].fact


def test_population_category_gets_measure_unit_and_source_evidence():
    source, _, _ = context('United Kingdom')
    items, _ = horizontal_trend_report(source)
    assert items[0].title == '영국 인구 추정치 변화'
    assert '100명' in items[0].fact and '120명' in items[0].fact
    assert "'Source'!A1" in items[0].evidence


def test_unfamiliar_geography_is_proved_by_axis_header_not_a_name_list():
    source, _, _ = context('New Borough', geography=True)
    items, _ = horizontal_trend_report(source)
    assert items[0].title == 'New Borough 인구 추정치 변화'
    assert "'Source'!A3" in items[0].evidence


@pytest.mark.parametrize('fmt', ['0%', '$0', '0" years"'])
def test_explicit_incompatible_units_prevent_population_count_label(fmt):
    source, _, _ = context('United Kingdom', fmt=fmt)
    items, _ = horizontal_trend_report(source)
    assert items and '인구 추정치' not in items[0].title and '100명' not in items[0].fact


def test_explicit_population_scale_is_preserved():
    source, _, _ = context('United Kingdom', declared='thousand persons')
    items, _ = horizontal_trend_report(source)
    assert '100 천 명' in items[0].fact and '100명' not in items[0].fact


@pytest.mark.parametrize('metric', ['Revenue', 'Customer count', 'Average age', 'Unknown measure'])
def test_price_caption_does_not_relabel_other_measure(metric):
    source, _, _ = context(metric, 'Average Price of Electricity by State', declared='Cents per Kilowatthour')
    items, _ = horizontal_trend_report(source)
    assert items and '전기요금' not in items[0].title


def test_price_category_needs_positive_dimension_and_rate_unit():
    source, _, _ = context('U.S. Total', 'Average Price of Electricity by State', basis='Residential', declared='Cents per Kilowatthour')
    items, _ = horizontal_trend_report(source)
    assert items[0].title == '가정용 · 미국 전체 평균 전기요금 변화'
    assert '100 센트/kWh' in items[0].fact


def test_a_second_table_cannot_borrow_population_caption():
    source, sheet, series = context('United Kingdom')
    rows = sheet['business_facts']['table_regions'][0]['rows']
    rows.extend([[{'cell': 'A8', 'value': 'Region'}, {'cell': 'B8', 'value': '2023-01-01'}, {'cell': 'C8', 'value': '2024-01-01'}],
                 [{'cell': 'A9', 'value': 'United Kingdom'}, {'cell': 'B9', 'value': 40}, {'cell': 'C9', 'value': 50}]])
    series['label_cell'] = 'A9'
    for point, col, val in zip(series['points'], 'BC', [40, 50]):
        point.update(period_cell=f'{col}8', value_cell=f'{col}9', value=val)
    items, _ = horizontal_trend_report(source)
    assert items and '인구 추정치' not in items[0].title and '40명' not in items[0].fact


@pytest.mark.parametrize('caption', ['Population estimates and births by region',
                                    'Population estimates & average age by region',
                                    'Population estimates / deaths by region'])
def test_mixed_measure_caption_cannot_assign_population_to_geography(caption):
    source, _, _ = context('United Kingdom', f'Table 4. {caption}')
    items, _ = horizontal_trend_report(source)
    assert items and '인구 추정치' not in items[0].title and '100명' not in items[0].fact


def test_conjunction_in_geographic_qualifier_does_not_block_population_caption():
    source, _, _ = context('United Kingdom', 'Population estimates: Summary for England and Wales')
    items, _ = horizontal_trend_report(source)
    assert items and '인구 추정치' in items[0].title
