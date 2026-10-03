"""Display-text cleanup. Raw values are never modified; callers keep both."""

EM_DASH = "\u2014"


def display_text(raw: str | None) -> str | None:
    """Replace em dash with ': ' when it separates a label from detail, else ' - '."""
    if raw is None:
        return None
    if EM_DASH not in raw:
        return raw
    parts = raw.split(EM_DASH)
    # A short leading fragment (no spaces, or ends without a verb-like word) reads like a label.
    head = parts[0].strip()
    if head and " " not in head:
        return ": ".join(p.strip() for p in parts)
    return " - ".join(p.strip() for p in parts)


def contains_em_dash(text: str | None) -> bool:
    return bool(text) and EM_DASH in text
