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
        masked = _remove_source_phrase(remaining.casefold(), source)
        if masked == remaining.casefold():
            continue
        label_remainder = source
        for start, end, *_ in reversed(mentions):
            label_remainder = label_remainder[:start] + label_remainder[end:]
        if mentions and not label_remainder.strip(" '\""):
            return remaining, "원본의 대상명과 요청 날짜가 같은 표현이어서 기간을 임의로 제한하지 않았습니다. 대상과 날짜 범위를 구분해 주세요."
        # Mask complete source names, including labels such as "Last 12 months".
        # Never remove standalone years from an independent requested date.
        remaining = masked
    return remaining, None
