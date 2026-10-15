"""Expose exhausted provider quota without leaking provider messages or secrets."""
from app.services.insights.models import InsightGenerationError

QUOTA_MESSAGE = ("AI 서비스 사용 한도가 소진되어 답변을 생성할 수 없습니다. "
                 "관리자가 API 이용 한도를 확인해야 합니다.")
_QUOTA_CODES = {"credit_balance_exhausted", "insufficient_quota"}


class QuestionQuotaExhaustedError(InsightGenerationError):
    def __init__(self):
        super().__init__(QUOTA_MESSAGE)


def raise_for_quota_exhaustion(exception):
    """Only explicit provider error codes qualify; ordinary 429s keep fallback."""
    seen = set()
    while exception is not None and id(exception) not in seen:
        seen.add(id(exception))
        if isinstance(exception, QuestionQuotaExhaustedError):
            raise QuestionQuotaExhaustedError() from None
        body = getattr(exception, "body", None)
        details = body.get("error", body) if isinstance(body, dict) else {}
        codes = [getattr(exception, key, None) for key in ("code", "type")]
        if isinstance(details, dict):
            codes.extend(details.get(key) for key in ("code", "type"))
        if any(isinstance(code, str) and code in _QUOTA_CODES for code in codes):
            raise QuestionQuotaExhaustedError() from None
        exception = exception.__cause__
