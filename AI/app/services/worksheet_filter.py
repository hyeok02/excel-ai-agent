from openpyxl.worksheet.worksheet import Worksheet

from app.services.analysis_inclusion import (
    AnalysisDecision,
    AnalysisInclusion,
    INCLUDED_BUSINESS_WORKSHEET,
)


SYSTEM_SHEET_NAMES = {
    "ciohiddencachesheet",
}


def is_business_worksheet(worksheet: Worksheet, include_hidden: bool = False) -> bool:
    """Return whether a worksheet should be included in user-facing analysis."""
    return (
        evaluate_worksheet_inclusion(worksheet, include_hidden).decision
        is AnalysisDecision.INCLUDE
    )


def evaluate_worksheet_inclusion(
    worksheet: Worksheet, include_hidden: bool = False
) -> AnalysisInclusion:
    """
    분석에 넣을지 판단하고 그 이유를 돌려준다.

    숨김 시트는 기본적으로 뺀다. 다만 계산 과정을 숨겨 두는 실무 파일이 있어,
    사용자가 켜면 보이는 시트와 똑같이 다룬다. 애드인이 만든 캐시 시트는
    사용자가 만든 내용이 아니므로 켜도 계속 뺀다.
    """
    if not include_hidden and worksheet.sheet_state != "visible":
        return AnalysisInclusion(
            decision=AnalysisDecision.EXCLUDE,
            reason_code="hidden_worksheet",
            reason=f"{worksheet.sheet_state} 상태의 숨김 시트로 분석에서 제외",
        )

    normalized_name = worksheet.title.strip().casefold()
    name_without_leading_underscores = normalized_name.lstrip("_")

    if normalized_name in SYSTEM_SHEET_NAMES:
        return AnalysisInclusion(
            decision=AnalysisDecision.EXCLUDE,
            reason_code="system_cache_worksheet",
            reason="Excel 또는 애드인이 생성한 시스템 캐시 시트로 분석에서 제외",
        )

    if name_without_leading_underscores.startswith("snloffice"):
        return AnalysisInclusion(
            decision=AnalysisDecision.EXCLUDE,
            reason_code="addin_cache_worksheet",
            reason="SNL Office 애드인이 생성한 쿼리 캐시 시트로 분석에서 제외",
        )

    return INCLUDED_BUSINESS_WORKSHEET
