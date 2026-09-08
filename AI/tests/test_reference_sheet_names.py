from app.services.insights.verification.validation_index import extract_references


def test_quoted_sheet_names_unescape_excel_apostrophes_without_colliding():
    owner = extract_references("'Owner''s Data'!A1")
    investor = extract_references("'Investor''s Data'!A1")

    assert owner == {"owner's data!a1"}
    assert investor == {"investor's data!a1"}
    assert owner.isdisjoint(investor)
