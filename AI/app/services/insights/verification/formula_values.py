"""A file whose formulas were saved without their results (written by a script, never opened in Excel)."""
SHARE = 0.5  # most formulas without a value: the file was saved that way, not a few blank IF results
FEW = 5


def unsaved_formula_notice(summary):
    """The sentence telling a reader that totals computed by formulas could not be read, or None."""
    formulas = [formula for sheet in summary.sheets for formula in sheet.formulas
                if '""' not in (formula.formula or "")]  # IF(B4=0,"",…) leaves no value on purpose
    missing = sum(formula.cached_value is None for formula in formulas)
    if len(formulas) < FEW or missing < SHARE * len(formulas):
        return None
    return (f"수식 {missing:,}개의 계산 결과가 파일에 저장되어 있지 않아, 합계·잔액처럼 수식으로 계산되는 값은 "
            "인사이트에 반영하지 못했습니다. Excel에서 파일을 열어 저장하면 반영됩니다.")
