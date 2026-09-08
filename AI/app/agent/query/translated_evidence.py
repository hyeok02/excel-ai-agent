from app.services.insights.display.glossary import translate


def translated_evidence_sources(evidence: list[object]) -> list[str]:
    """Allow only glossary translations backed by the cited source values."""
    translations = []
    for item in evidence:
        for field in ("description", "value"):
            value = getattr(item, field, None)
            if isinstance(value, str) and (translated := translate(value)):
                translations.append(translated)
    return translations
