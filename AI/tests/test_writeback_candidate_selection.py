from io import BytesIO

from openpyxl import Workbook

from app.agent.query.index import build_workbook_data_index
from app.agent.writeback.candidates import select_writeback_candidates


def _workbook_with_a_wide_leading_sheet() -> bytes:
    """
    앞에 넓은 시트, 뒤에 정답 셀이 있는 워크북.

    실제 사고가 난 워크북의 구조를 줄여서 재현한다. 앞 시트가 후보 수 상한을
    다 써버리면 뒤 시트의 정답 셀이 모델에게 전달되지 않는다.
    """
    workbook = Workbook()
    wide = workbook.active
    wide.title = "Overview"
    wide.append([f"Metric {column}" for column in range(40)])
    for row in range(60):
        # 요청에 적을 값(1081)과 겹치지 않는 범위로 채운다.
        wide.append([50_000 + row * 40 + column for column in range(40)])

    detail = workbook.create_sheet("Headcount")
    detail.append(["Department", "Services", "Support"])
    detail.append(["2025-06-01", 1081, 7])
    detail.append(["2023-09-01", 1277, 11])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _references(instruction: str) -> set[str]:
    content = _workbook_with_a_wide_leading_sheet()
    index = build_workbook_data_index("headcount.xlsx", content)
    return {cell.reference for cell in select_writeback_candidates(instruction, index)}


def test_cell_holding_the_stated_value_reaches_the_model() -> None:
    references = _references("Services 인원을 1081에서 981로 줄여줘")

    assert "Headcount!B2" in references


def test_wide_leading_sheet_does_not_crowd_out_the_stated_value() -> None:
    references = _references("Services 인원을 1081에서 981로 줄여줘")
    overview_cells = {item for item in references if item.startswith("Overview!")}

    assert "Headcount!B2" in references
    assert len(overview_cells) < len(references)


def test_selection_still_works_without_a_stated_value() -> None:
    references = _references("Headcount 시트 Services 값을 981로 바꿔줘")

    assert any(item.startswith("Headcount!") for item in references)
