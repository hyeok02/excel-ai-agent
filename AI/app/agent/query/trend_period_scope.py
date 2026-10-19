"""Do not mistake a source-bound identifier's year for a requested period."""
from app.agent.query.metric_request_coverage import _remove_source_phrase
from app.agent.query.question_date_mentions import calendar_mentions
from app.agent.query.trend_labels import trend_label_spellings


def calendar_request(question, observations, named_sheets=()):
    sources = {str(cell.value) for item in observations for cell in item.entity_cells}
    sources.update(named_sheets)
    sources.update(label for item in observations for label in trend_label_spellings(item.label.value))
    remaining = question
    for source in sorted(sources, key=len, reverse=True):
        mentions = calendar_mentions(source)
        if not mentions:
            continue
        masked = _remove_source_phrase(remaining.casefold(), source)
        if masked == remaining.casefold():
            continue
        label_remainder = source
        for start, end, *_ in reversed(mentions):
            label_remainder = label_remainder[:start] + label_remainder[end:]
        if not label_remainder.strip(" '\""):
            return remaining, "원본의 대상명과 요청 날짜가 같은 표현이어서 기간을 임의로 제한하지 않았습니다. 대상과 날짜 범위를 구분해 주세요."
        # Remove only the complete source name, never all occurrences of its
        # year: 'Project 2024 ... 2025년' must retain the independent date.
        remaining = masked
    return remaining, None
