from app.services.insights.display.glossary import readable, translate


def test_known_terms_keep_the_original_beside_the_reading() -> None:
    assert readable("Revenue") == "매출(Revenue)"
    assert readable("EBITDA") == "상각전영업이익(EBITDA)"
    assert readable("KEY DEVELOPMENTS") == "주요 사건(KEY DEVELOPMENTS)"
    assert readable("Services") == "서비스(Services)"


def test_unknown_terms_are_shown_exactly_as_written() -> None:
    assert readable("Weird Column Name") == "Weird Column Name"
    assert translate("Weird Column Name") == ""


def test_korean_source_headers_are_left_alone() -> None:
    assert readable("전체 직원 수") == "전체 직원 수"
    assert translate("매출") == ""


def test_header_paths_are_read_part_by_part() -> None:
    assert translate("Department > General & Administrative") == "부서 > 일반관리"
    assert translate("Department > Unlisted Team") == ""


def test_blank_and_oversized_values_are_never_translated() -> None:
    assert readable(None) == ""
    assert translate("") == ""
    assert translate("Revenue " * 20) == ""
