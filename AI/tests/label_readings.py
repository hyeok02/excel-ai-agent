"""Stand-in for the model's Korean label readings, so tests can fix what a workbook's labels read as."""
from contextlib import contextmanager

import app.agent  # noqa: F401  (import order: the insight package imports the agent package)

from app.services.insights.display import label_translator


@contextmanager
def readings(mapping):
    """``mapping``: label -> Korean, or label -> (Korean, counter word)."""
    saved = dict(label_translator._READINGS), dict(label_translator._COUNTERS)
    for label, read in mapping.items():
        korean, unit = read if isinstance(read, tuple) else (read, "")
        label_translator._READINGS[label.casefold()] = korean
        if unit:
            label_translator._COUNTERS[label.casefold()] = unit
    try:
        yield
    finally:
        for store, kept in zip((label_translator._READINGS, label_translator._COUNTERS), saved):
            store.clear()
            store.update(kept)


# What a model reads these test workbooks' labels as; tests that check Korean prose use it.
MODEL_READINGS = {
    "Actual": "실적", "Forecast": "전망", "Total Generation": "총 발전량", "Natural Gas": "천연가스",
    "Annual Totals": "연간 합계", "Year to Date": "연초 이후 누적", "Thousand Megawatthours": "천 MWh",
    "Adult beds": "성인 병상", "Children beds": "아동 병상", "Available": "가용", "Occupied": "사용",
    "Cents per Kilowatthour": "센트/kWh", "Grand Total": "총합계", "Occupancy rate": "점유율",
    "Total sales": "총매출",
    "Electricity generation by energy source, 2025-2026": "에너지원별 발전량, 2025-2026",
    "Percentage of days with good, moderate, or unhealthy air quality for children ages 0 to 17 years, 1999-2023":
        "1년 전체 날짜 중 각 공기질 등급에 해당하는 날의 비율 (0~17세 아동, 1999-2023)",
    "air quality": "공기질", "Good": "좋음", "Moderate": "보통", "Unhealthy": "건강에 해로움",
}
