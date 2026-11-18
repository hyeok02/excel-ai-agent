"""A draft whose claims all fail still answers an open question when its numbers are cited values."""
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.execution.models import AgentExecutionEvidence
from app.agent.query.claim_models import SourceClaim
from app.agent.query.grounded_interpretation import INTERPRETED, interpreted_answer
from app.agent.query.models import QuestionAnswerDraft

FACT = "지역별로 보면 ‘NY’의 보험가액 합계가 1,492,252,118로 가장 큽니다. 이 항목은 전체 보험가액의 60.12%를 차지합니다."


def _cell(reference, value, header, style="General"):
    return AgentExecutionEvidence(kind="cell", sheet_name="CatReg", reference=reference, description=header,
                                  value=value, number_format=style)


def _execution():
    cells = [_cell("A4", "Category", "Category"), _cell("A6", "Cookies", "Category"),
             _cell("B6", 10683.5, "East", "$#,##0"), _cell("C6", 6528.91, "West", "$#,##0")]
    data = {"verified_insights": [{"fact": FACT, "support_references": ["CatReg!B6"]}]}
    return SimpleNamespace(steps=[SimpleNamespace(status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
                                                  result=SimpleNamespace(evidence=cells, data=data))])


def _draft(answer, claims):
    return QuestionAnswerDraft(answer=answer, evidence=[], confidence=1.0, limitations=[], claims=claims)


CELLS = [SourceClaim(kind="cell_value", value_reference=f"CatReg!{column}6") for column in "BC"]


def test_cited_values_are_shown_with_source_labels_and_the_prose_as_interpretation():
    answer = interpreted_answer("동부가 많은 이유는?", _draft(
        "쿠키에서 동부가 $10,683.50로 서부 $6,528.91보다 많기 때문입니다.", CELLS), _execution())
    assert answer.answer.splitlines()[:3] == ["근거(원본 확인):", "· CatReg — Cookies · East: $10,683.50",
                                              "· CatReg — Cookies · West: $6,528.91"]
    assert answer.answer.endswith("해석: 쿠키에서 동부가 $10,683.50로 서부 $6,528.91보다 많기 때문입니다.")
    assert answer.status == "limited" and answer.limitations == [INTERPRETED]
    assert {item.reference for item in answer.evidence} == {"A6", "B6", "C6"}


def test_a_sentence_with_a_number_no_cited_value_holds_is_dropped():
    answer = interpreted_answer("동부가 많은 이유는?", _draft(
        "동부가 서부보다 63% 많습니다. 쿠키는 동부 $10,683.50입니다.", CELLS), _execution())
    assert answer.answer.endswith("해석: 쿠키는 동부 $10,683.50입니다.")
    assert interpreted_answer("이유는?", _draft("동부가 서부보다 63% 많습니다.", CELLS), _execution()) is None
    assert interpreted_answer("이유는?", _draft("동부가 더 많습니다.", []), _execution()) is None  # nothing cited


def test_a_quoted_verified_fact_grounds_its_own_numbers():
    answer = interpreted_answer("큰 계약의 공통점은?", _draft(
        "큰 계약은 주로 NY에 있으며 전체의 60.12%를 차지합니다.",
        [SourceClaim(kind="verified_fact", fact=FACT)]), _execution())
    assert answer.answer == f"근거(원본 확인):\n· {FACT}\n\n해석: 큰 계약은 주로 NY에 있으며 전체의 60.12%를 차지합니다."


def test_a_difference_is_grounded_when_its_two_cited_values_are_stated_with_it():
    answer = interpreted_answer("동부가 많은 이유는?", _draft(
        "쿠키는 동부 $10,683.50, 서부 $6,528.91로 동부가 $4,154.59 많습니다.", CELLS), _execution())
    assert answer is not None and "$4,154.59" in answer.answer
    assert interpreted_answer("이유는?", _draft("쿠키는 동부가 $4,154.59 많습니다.", CELLS), _execution()) is None


def test_a_fact_whose_cells_the_search_did_not_return_cites_them_from_the_workbook():
    from app.agent.query.index import IndexedCell
    execution = _execution()
    execution.steps[0].result.data["verified_insights"][0]["support_references"] = ["'Policy'!F9", "'Policy'!F2:F501"]
    index = SimpleNamespace(rows=[SimpleNamespace(cells=[IndexedCell("Policy", "F9", 1492252118, None, "number")])])
    draft = _draft("큰 계약은 NY에 있으며 전체의 60.12%입니다.", [SourceClaim(kind="verified_fact", fact=FACT)])
    assert interpreted_answer("공통점은?", draft, execution) is None  # nothing to cite without the workbook
    answer = interpreted_answer("공통점은?", draft, execution, index=index)
    assert [item.reference for item in answer.evidence] == ["F9"] and answer.answer.endswith("전체의 60.12%입니다.")


def _rows(labels):
    cells = [cell for row, (label, qty) in enumerate(labels, 2)
             for cell in (AgentExecutionEvidence(kind="cell", sheet_name="Sales", reference=f"A{row}", description="ID",
                                                 value=label, number_format="General"),
                          AgentExecutionEvidence(kind="cell", sheet_name="Sales", reference=f"D{row}", description="Qty",
                                                 value=qty, number_format="General"))]
    execution = SimpleNamespace(steps=[SimpleNamespace(status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
                                                       result=SimpleNamespace(evidence=cells, data={}))])
    claims = [SourceClaim(kind="cell_value", value_reference=f"Sales!D{row}") for row in (2, 3)]
    return interpreted_answer("실적을 개선하려면?", _draft("판매수량이 33에서 44로 11 증가했습니다. 수량은 33과 44입니다.", claims),
                              execution)


def test_a_rise_between_two_records_is_no_trend_while_one_between_two_periods_is():
    # Two transactions are no trend, and values no sentence ties to their record are no basis either.
    assert _rows([("ID07351", 33), ("ID07594", 44)]) is None
    assert _rows([(2023, 33), (2024, 44)]).answer.endswith("해석: 판매수량이 33에서 44로 11 증가했습니다. 수량은 33과 44입니다.")


def test_the_nearest_header_names_the_column_and_an_unstated_cell_is_no_basis():
    execution = _execution()
    execution.steps[0].result.evidence += [_cell("B3", "Region", "Region"), _cell("B4", "East", "East")]
    claims = [SourceClaim(kind="cell_value", value_reference="CatReg!B6", property_reference="CatReg!B3"),
              SourceClaim(kind="cell_value", value_reference="CatReg!C6")]
    execution.steps[0].result.data["source_header_bindings"] = {"catreg!b6": "CatReg!B4"}
    answer = interpreted_answer("동부가 많은 이유는?", _draft("쿠키에서 동부가 $10,683.50로 많기 때문입니다.", claims), execution)
    # 'Region' is the pivot's field name above 'East'; West's cell is cited but never stated.
    assert answer.answer.splitlines()[1:3] == ["· CatReg — Cookies · East: $10,683.50", ""]


def test_cited_cells_no_sentence_states_are_no_basis_for_a_reading():
    assert interpreted_answer("개선하려면?", _draft("쿠키 같은 주요 품목에 집중하는 것이 좋습니다.", CELLS), _execution()) is None


def test_a_period_named_by_a_header_is_grounded_as_the_sentence_writes_it():
    cells = [_cell("A4", "State", "State"), _cell("B4", "August 2026", "August 2026"), _cell("A5", "Hawaii", "State"),
             _cell("B5", 47.18, "August 2026", "0.00")]
    execution = SimpleNamespace(steps=[SimpleNamespace(status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
                                                       result=SimpleNamespace(evidence=cells, data={}))])
    claim = SourceClaim(kind="cell_value", value_reference="CatReg!B5", property_reference="CatReg!B4")
    answer = interpreted_answer("비싼 지역의 특징은?", _draft("Hawaii는 2026년 8월 47.18로 가장 높습니다.", [claim]), execution)
    assert answer.answer == ("근거(원본 확인):\n· CatReg — Hawaii · August 2026: 47.18\n\n"
                             "해석: Hawaii는 2026년 8월 47.18로 가장 높습니다.")


def test_a_value_read_from_one_record_is_not_kept_as_a_group_value():
    cells = [AgentExecutionEvidence(kind="cell", sheet_name="Sales", reference=reference, description=header,
                                    value=value, number_format="General")
             for reference, value, header in [("A2", "ID07351", "ID"), ("D2", "Boston", "City"), ("I2", 58.41, "TotalPrice"),
                                              ("A3", "ID07594", "ID"), ("D3", "Los Angeles", "City"), ("I3", 124.96, "TotalPrice")]]
    execution = SimpleNamespace(steps=[SimpleNamespace(status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
                                                       result=SimpleNamespace(evidence=cells, data={}))])
    claims = [SourceClaim(kind="cell_value", value_reference=f"Sales!I{row}") for row in (2, 3)]
    city = _draft("Boston의 판매금액은 58.41이고, Los Angeles의 판매금액은 124.96입니다.", claims)
    assert interpreted_answer("Boston과 LA 판매금액 차이는?", city, execution) is None  # one sale each, not the cities
    record = _draft("ID07351 거래는 58.41, ID07594 거래는 124.96입니다.", claims)
    assert interpreted_answer("두 거래 금액은?", record, execution).answer.endswith("해석: ID07351 거래는 58.41, ID07594 거래는 124.96입니다.")


def test_a_figure_the_draft_rounds_still_states_its_cited_cell():
    cells = [_cell("A52", "Domestic transport total", "TES"), _cell("D52", 124.19116920681061, "1990", "0.0"),
             _cell("E52", 110.3864012837939, "2024", "0.0")]
    execution = SimpleNamespace(steps=[SimpleNamespace(status=AgentStepStatus.SUCCEEDED, tool_name="search_workbook_data",
                                                       result=SimpleNamespace(evidence=cells, data={}))])
    claims = [SourceClaim(kind="cell_value", value_reference=f"CatReg!{column}52") for column in "DE"]
    answer = interpreted_answer("얼마나 줄었어?", _draft("124.2에서 110.4로 감소했습니다.", claims), execution)
    assert answer is not None and len(answer.answer.splitlines()) == 5  # header, two cited cells, blank, reading
