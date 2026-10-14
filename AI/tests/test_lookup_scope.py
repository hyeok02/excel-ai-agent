"""검색이 표가 있는 시트를 놓쳐도 조회가 되는지, 그 근거가 실리는지."""
from app.agent.contracts import AgentToolContext
from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.tools.workbook_data import WorkbookDataSearchTool
from app.services.workbook_parsing.models import WorkbookSummary

NOISE = "TAG목록"
TABLE = "작업현황"
HEADERS = {"C": "IP", "D": "장비"}
QUESTION = "CVD #2 IP가 뭐야?"


def _row(sheet: str, number: int, values: dict[str, object]) -> IndexedRow:
    return IndexedRow(
        sheet, number,
        tuple(
            IndexedCell(sheet, f"{column}{number}", value, None)
            for column, value in values.items()
        ),
    )


def _index() -> WorkbookDataIndex:
    rows = [_row(NOISE, number, {"A": f"CVD IP TAG {number}"}) for number in range(1, 31)]
    rows.append(_row(TABLE, 5, HEADERS))
    rows.extend(
        _row(TABLE, number, {"C": f"10.1.7.{number}", "D": f"CVD #{number - 5}"})
        for number in range(6, 12)
    )
    return WorkbookDataIndex("tck.xlsx", tuple(rows), len(rows) * 2, False)


def _executed(question: str = QUESTION):
    index = _index()
    context = AgentToolContext(WorkbookSummary("tck.xlsx", 0, []), index, question)
    return WorkbookDataSearchTool().execute(context, {"query": question})


def test_widens_to_the_whole_workbook_when_the_searched_sheets_answer_nothing() -> None:
    result = _executed()

    assert result.data["cell_lookup"]["label"] == "CVD #2"
    assert result.data["cell_lookup"]["value"] == "10.1.7.7"


def test_carries_the_widened_lookup_cells_as_evidence() -> None:
    # 조회한 셀이 근거에 없으면 답변이 통째로 "근거 부족"으로 버려진다.
    result = _executed()
    found = result.data["cell_lookup"]
    present = {f"{item.sheet_name}!{item.reference}" for item in result.evidence}

    for key in ("header_reference", "label_reference", "value_reference"):
        assert found[key] in present
