"""Knowledge base domain logic — pure validation and search ranking.

No project imports; stdlib + dataclasses only.
"""

from __future__ import annotations

ANNOTATION_TYPES: frozenset[str] = frozenset({"code", "data", "gfx", "audio", "text"})
VARIABLE_TYPES: frozenset[str] = frozenset({"u8", "u16", "bool", "enum"})
MAX_ADDRESS = 0xFFFF
MAX_SEARCH_RESULTS = 50
ROM_ADDRESS_LIMIT = 0x8000


def validate_annotation_type(value: str | None) -> None:
    """Raise ValueError if *value* is not a valid annotation type (None is allowed)."""
    if value is not None and value not in ANNOTATION_TYPES:
        valid = sorted(ANNOTATION_TYPES)
        msg = f"Invalid annotation type: {value!r}. Must be one of {valid}."
        raise ValueError(msg)


def validate_variable_type(value: str) -> None:
    """Raise ValueError if *value* is not a valid variable type."""
    if value not in VARIABLE_TYPES:
        valid = sorted(VARIABLE_TYPES)
        msg = f"Invalid variable type: {value!r}. Must be one of {valid}."
        raise ValueError(msg)


def validate_address(address: int) -> None:
    """Raise ValueError if *address* is outside the 16-bit range [0, 0xFFFF]."""
    if address < 0 or address > MAX_ADDRESS:
        hi = f"0x{MAX_ADDRESS:X}"
        msg = f"Invalid address: 0x{address:X}. Must be between 0x0000 and {hi}."
        raise ValueError(msg)


def validate_name(name: str, field: str = "name") -> None:
    """Raise ValueError if *name* is empty or whitespace-only."""
    if not name or not name.strip():
        msg = f"Invalid {field}: must be a non-empty string."
        raise ValueError(msg)


def rank_search_results(results: list[dict], query: str) -> list[dict]:
    """Sort *results* by relevance to *query* and cap at 50.

    Ranking tiers (lower is better):
    0 — exact match (case-insensitive)
    1 — prefix match
    2 — substring match
    3 — no match on the ranking key (keep original order)
    """
    query_lower = query.lower()

    def _rank_key(result: dict) -> int:
        text = result.get("label") or result.get("name") or ""
        text_lower = text.lower()
        if text_lower == query_lower:
            return 0
        if text_lower.startswith(query_lower):
            return 1
        if query_lower in text_lower:
            return 2
        return 3

    ranked = sorted(results, key=_rank_key)
    return ranked[:MAX_SEARCH_RESULTS]


def calculate_coverage_pct(annotated: int, total_addresses: int) -> float:
    """Return ROM coverage percentage: annotated / total_addresses * 100.

    Returns 0.0 if *total_addresses* is zero.
    """
    if total_addresses == 0:
        return 0.0
    return annotated / total_addresses * 100
