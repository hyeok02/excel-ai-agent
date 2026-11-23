"""A parse for insights samples whole tables; any other parse keeps the smaller sample questions use."""
from io import BytesIO

from openpyxl import Workbook

from app.services.workbook_details.sample_caps import wider_samples
from app.services.workbook_parser import parse_workbook


def _wide_sheet():
    book = Workbook()
    for number in range(1, 1_002):
        book.active.append([f"r{number}", *range(20)])  # 21 columns × 1,001 rows: past 16,384 cells
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


def test_only_a_parse_for_insights_reads_the_whole_table():
    content = _wide_sheet()
    sampled = sum(len(row) for region in parse_workbook("w.xlsx", content).sheets[0].regions
                  for row in region.analysis_rows)
    with wider_samples():
        whole = sum(len(row) for region in parse_workbook("w.xlsx", content).sheets[0].regions
                    for row in region.analysis_rows)
    assert sampled <= 16_384 < whole == 21 * 1_001
