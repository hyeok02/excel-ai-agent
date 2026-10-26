"""Prefer the explicitly requested card without bypassing its proof checks."""
from app.agent.query.verified_insight_matching import _TOKENS, _request_word


def requested_insight_items(question, items):
    items = list(items)
    asked = _content_tokens(question)
    exact = [item for item in items
             if asked and asked == _content_tokens(str(item.get("title") or ""))]
    # Do not answer with an overlapping card if the exact card lacks evidence.
    # Duplicate exact titles remain ambiguous in the ordinary score/tie gate.
    return exact or items


def _content_tokens(text):
    return tuple(token for token in _TOKENS.findall(text.casefold()) if not _request_word(token))
