"""계산 결과가 오류로 남은 셀을 잡는 규칙 검증."""
from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.analyzer import _deduplicated
from app.services.formula_risks.error_values import detect_error_values, error_code


def formula(cell: str, cached, text: str = "=VLOOKUP(A1,B:C,2,FALSE)") -> FormulaAnalysis:
    return FormulaAnalysis(cell=cell, formula=text, references=[], cached_value=cached)


def test_finds_every_excel_error_code():
    sheet = [formula(f"A{index}", code) for index, code in enumerate(
        ["#N/A", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#NULL!"], start=1
    )]

    found = detect_error_values([("매출", sheet)])

    assert len(found) == 7
    assert {item.severity for item in found} == {"error"}
    assert {item.kind for item in found} == {"cached_error"}


def test_explains_the_error_and_keeps_the_code():
    found = detect_error_values([("매출", [formula("B2", "#DIV/0!")])])[0]

    assert found.sheet_name == "매출" and found.cell == "B2"
    assert "#DIV/0!" in found.message and "0으로 나누고" in found.message
    assert found.observed_value == "#DIV/0!"


def test_leaves_normal_results_alone():
    sheet = [formula("A1", 1081), formula("A2", "서비스"), formula("A3", None),
             formula("A4", True), formula("A5", "N/A 아님")]

    assert detect_error_values([("매출", sheet)]) == []


def test_reads_the_code_case_insensitively_and_ignores_the_rest():
    assert error_code("#n/a") == "#N/A"
    assert error_code(" #DIV/0! ") == "#DIV/0!"
    assert error_code("#UNKNOWN!") is None
    assert error_code(1081) is None


def test_the_same_cell_is_not_reported_twice_for_the_same_reason():
    # 한 수식이 같은 외부 파일을 여러 번 참조하면 참조마다 한 건씩 쌓인다.
    findings = detect_error_values([("매출", [formula("B2", "#N/A")] * 3)])

    assert len(_deduplicated(findings)) == 1


def external(cell: str, reference: str):
    from app.services.formula_risks.finding_factory import build_formula_finding
    return build_formula_finding(
        "external_reference", "warning", "재무", formula(cell, None, "=INDEX(...)"),
        "다른 Excel 파일을 참조합니다.", reference=reference,
    )


def test_one_cell_linking_to_one_external_file_is_reported_once():
    findings = [
        external("B97", "'[2]Language Index'!$A$8:$A$9906"),
        external("B97", "'[2]Language Index'!$B$8:$B$9906"),
        external("B97", "'[3]Other'!$A$1:$A$9"),
    ]

    unique = _deduplicated(findings)

    assert [item.reference for item in unique] == [
        "'[2]Language Index'!$A$8:$A$9906",
        "'[3]Other'!$A$1:$A$9",
    ]
