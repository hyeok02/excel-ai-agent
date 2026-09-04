import pytest

from app.services.insights.claim_grounding import grounded_claim
from app.services.insights.unit_grounding import grounded_units


SOURCE = ["급식 열량", "750", "급식 열량은 750 kcal입니다."]
REFERENCES = {"sheet1!a2:c2"}


def test_person_count_is_not_generic_grammar_for_a_calorie_source():
    assert not grounded_claim("급식 열량은 750명입니다.", SOURCE, REFERENCES)
    assert not grounded_claim("급식 열량은 750 명입니다.", SOURCE, REFERENCES)


@pytest.mark.parametrize("unit", ["%", "％", "percent", "퍼센트"])
def test_cannot_relabel_a_calorie_value_as_a_percentage(unit):
    assert not grounded_units(f"급식 열량은 750 {unit}입니다.", SOURCE, REFERENCES, [])


def test_person_unit_is_allowed_when_present_in_the_actual_source():
    assert grounded_claim("직원 수는 750명입니다.", ["직원 수", "750명"], REFERENCES)


@pytest.mark.parametrize("source", ["비중 25%", "비중(%)", "25 percent", "25 퍼센트"])
def test_keeps_percentages_explicitly_present_in_the_cited_source(source):
    assert grounded_units("원본 값은 25%입니다.", [source, "25"], REFERENCES, [])


def _change():
    return {
        "change_rate_percent": -11.21,
        "evidence": ["Sheet1!A2:C2", "Sheet1!A8:C8"],
    }


def test_keeps_computed_rate_only_with_all_change_evidence_cited():
    references = {*REFERENCES, "sheet1!a8:c8"}

    assert grounded_units("값은 11.21% 감소했습니다.", SOURCE, references, [_change()])
    assert not grounded_units("값은 11.21% 감소했습니다.", SOURCE, REFERENCES, [_change()])
    assert not grounded_units("값은 750% 감소했습니다.", SOURCE, references, [_change()])


def test_small_cell_citation_cannot_borrow_a_larger_change_range():
    assert not grounded_units(
        "값은 11.21%입니다.", SOURCE,
        {"sheet1!a2", "sheet1!a8"}, [_change()],
    )


def test_source_quotes_and_original_nonpercentage_units_are_preserved():
    assert grounded_units("원본에는 ‘열량(kcal)’ · ‘750’이 기록되어 있습니다.", SOURCE, REFERENCES, [])
    assert grounded_units("원본에 기록된 내용은 ‘섭취 비율 25%’입니다.", ["섭취 비율 25%"], REFERENCES, [])


@pytest.mark.parametrize("rate", [None, True, float("nan"), "invalid"])
def test_invalid_computed_rates_do_not_authorize_percentage_prose(rate):
    change = {**_change(), "change_rate_percent": rate}
    assert not grounded_units(
        "값은 11.21%입니다.", SOURCE, {*REFERENCES, "sheet1!a8:c8"}, [change],
    )
