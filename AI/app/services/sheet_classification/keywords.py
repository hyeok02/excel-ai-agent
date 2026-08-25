from app.services.sheet_classification.models import SheetRole

NAME_KEYWORDS: dict[SheetRole, tuple[str, ...]] = {
    SheetRole.INPUT: (
        "input", "raw", "source", "data", "입력", "원본", "기초", "가정", "기준값"
    ),
    SheetRole.CALCULATION: (
        "calc", "calculation", "model", "intermediate", "계산", "산출", "중간", "모델"
    ),
    SheetRole.OUTPUT: (
        "output", "summary", "report", "dashboard", "result",
        "요약", "보고", "결과", "현황", "대시보드",
    ),
    SheetRole.DOCUMENTATION: (
        "instruction", "guide", "readme", "help", "note",
        "안내", "설명", "도움말", "사용법", "주의사항",
    ),
}

SYSTEM_REASON_CODES = {"system_cache_worksheet", "addin_cache_worksheet"}
