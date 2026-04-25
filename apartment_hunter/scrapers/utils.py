import re


def parse_promo(text: str) -> str | None:
    """Extract promotion summary from any block of text."""
    if not text:
        return None

    # Match "N weeks/months free" (most common)
    m = re.search(
        r"(?:up\s+to\s+)?(\d+)\s*(weeks?|wks?|months?)\s*(?:rent\s+)?free"
        r"|look\s*(?:and|&)\s*lease\s*\w*"
        r"|(?:waived|free)\s+(?:app(?:lication)?\s+)?(?:admin\s+)?fee",
        text, re.IGNORECASE,
    )
    if not m:
        # Dollar-off discounts
        m = re.search(r"\$[\d,]+\s*(?:off|discount|credit|savings?)", text, re.IGNORECASE)
    if not m:
        return None

    promo = m.group(0).strip()

    # Try to find an end / expiry date anywhere in the same text
    end_m = re.search(
        r"(?:offer\s+)?ends?\s+(?:on\s+)?"
        r"(?P<date>[A-Za-z]+\.?\s+\d{1,2}(?:,?\s*\d{4})?|\d{1,2}/\d{1,2}(?:/\d{2,4})?)"
        r"|(?:valid\s+through|through|thru|until|expires?(?:\s+on)?)\s+(?P<date2>[A-Za-z]+\.?\s+\d{1,2}(?:,?\s*\d{4})?|\d{1,2}/\d{1,2}(?:/\d{2,4})?)",
        text, re.IGNORECASE,
    )
    if end_m:
        end_date = end_m.group("date") or end_m.group("date2")
        if end_date:
            promo += f" · ends {end_date.strip()}"

    return promo
