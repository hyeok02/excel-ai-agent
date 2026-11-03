from app.services.insights.display.source_labels import narrative_scope, section_label, source_caption, source_label, source_unit


def test_metric_vocabulary_composes_modifiers_without_selecting_source():
    assert source_label('Total greenhouse gas emissions') == '총 온실가스 배출량'
    assert source_label('Estimated greenhouse gas emissions') == '추정 온실가스 배출량'
    assert source_label('Residential · U.S. Total') == '가정용 · 미국 전체'
    assert source_label('Other forecast greenhouse gas emissions') == 'Other 전망 온실가스 배출량'
    assert source_label('Sales') == 'Sales'
    assert source_label('New mystery measure') == 'New mystery measure'


def test_units_are_translated_not_rescaled_or_guessed():
    assert source_unit('Thousand Megawatthours') == '천 MWh'
    assert source_unit('Cents per Kilowatthour') == '센트/kWh'
    assert source_unit('million tonnes carbon dioxide equivalent') == '백만 톤 CO₂환산량'
    assert source_unit('Units per case') == 'Units per case'
    assert source_unit('') == ''


def test_ambiguous_categories_require_context():
    assert source_label('Good') == 'Good'
    assert source_label('Good', 'Air quality') == '좋음'
    assert source_label('G&A') == 'G&A'
    assert source_label('G&A beds occupied') == '일반·급성기 사용 병상 수'
    assert source_label('G&A occupancy rate', 'all acute trusts') == '일반·급성기 병상 점유율'
    assert source_label('Available') == 'Available'
    assert source_label('Adult beds · Available') == '성인 병상 · 가용'
    assert source_label('Occupancy rate') == '점유율'


def test_air_quality_share_caption_explains_the_denominator():
    caption = source_label(
        'Percentage of days with good, moderate, or unhealthy air quality for '
        'children ages 0 to 17 years, 1999-2023'
    )
    assert caption == '1년 전체 날짜 중 각 공기질 등급에 해당하는 날의 비율 (0~17세 아동, 1999~2023년)'


def test_sections_preserve_comparison_basis_and_only_drop_opaque_sheet_names():
    assert narrative_scope('Sheet1', 'Annual Totals') == '연간 합계'
    assert narrative_scope('Table_1_01', 'Year to Date') == '연초 이후 누적'
    assert narrative_scope('Seoul plant', 'Budget') == 'Seoul plant · 예산'
    assert section_label('Year 2026') == '2026년'
    assert section_label('Year to Date') == '연초 이후 누적'


def test_source_qualifiers_and_age_are_not_discarded():
    assert source_label('Forecast Current Asthma Prevalence') == '전망 현재 천식 유병률'
    assert source_label('Children ages 5 to 12 years') == '5~12세 아동'
    assert source_label('Total Generation at Utility Scale Facilities') == '대규모 발전시설의 총발전량'
    assert source_label('Total Generation at Pilot Facilities') == 'Pilot Facilities의 총발전량'


def test_captions_translate_explicit_topics_without_losing_source_qualifiers():
    assert source_caption('Indicator Z9. Percentage of children ages 5 to 12 years with asthma, 2001-2022') == '5~12세 아동의 천식 유병률, 2001~2022년'
    assert source_caption('ABC7: Population estimates: Summary for Scotland, mid-2002 to mid-2023') == '스코틀랜드 인구 추정치 요약, 2002년 중반~2023년 중반'
    caption = source_caption('Table 3.2: Provisional Territorial greenhouse gas emissions by gas, in million tonnes carbon dioxide equivalent, UK 1991-2025')
    assert all(word in caption for word in ['잠정', '국내 발생', '온실가스 배출량', '가스별', '백만 톤 CO₂환산량', '영국', '1991~2025년'])
    assert 'Table 3.2' not in caption
    assert source_caption('Table 2.9: Mystery observations in East Laboratory, 2012-2023') == 'Mystery observations in East Laboratory, 2012~2023년'


def test_table_suffix_date_connector_and_duplicate_total_are_generic():
    caption = source_caption('Table 8.2.B. Average Price of Electricity by State, September 2024 and 2023')
    assert caption == '평균 전기요금 주별, 2024년 9월 및 2023년'
    assert source_label('Electricity supply total · Total') == '전력 공급 전체'
    assert source_label('Forecast Mystery total · Total') == '전망 Mystery 전체'
    assert source_label('Mystery total · Total (provisional)') == 'Mystery 전체 · 전체 (잠정)'
