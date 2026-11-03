"""Bounded source notes whose status qualifications belong to numeric facts."""
import re


def source_notes(regions):
    """Retain bounded, source-addressed status notes even when tables omit prose.

    Long footnotes are intentionally absent from numeric table samples. Their
    explicit year/status qualifications still matter to a reported figure, so
    keep the original cell text without truncating a sentence or its negation.
    """
    result, seen, size = [], set(), 0
    for region in regions:
        for row in region.get("analysis_rows", []):
            for cell in row:
                address, value = cell.get("address"), cell.get("value")
                if not address or address in seen or not isinstance(value, str):
                    continue
                if (not re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", value)
                        or not re.search(
                            r"\b(?:preliminary|provisional|final|revised)\b|잠정|확정|수정치",
                            value, re.I,
                        )):
                    continue
                if len(value) > 8000 or size + len(value) > 16000:
                    continue
                result.append({"cell": address, "value": value})
                seen.add(address)
                size += len(value)
                if len(result) >= 20:
                    return result
    return result
