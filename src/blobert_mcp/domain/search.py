"""Byte pattern search and string detection for ROM analysis.

No project imports; stdlib only.
"""

from __future__ import annotations


def _parse_pattern(pattern: str) -> list[int | None]:
    """Parse a hex pattern string into a list of byte values or None wildcards.

    Pattern syntax: space-separated tokens of exactly 2 hex characters each,
    or ``??`` for a single-byte wildcard.

    Raises ValueError for empty patterns, invalid hex, or malformed tokens.
    """
    tokens = pattern.strip().split()
    if not tokens:
        msg = "Empty pattern"
        raise ValueError(msg)
    result: list[int | None] = []
    for token in tokens:
        if token == "??":
            result.append(None)
        elif len(token) != 2:
            msg = f"Invalid pattern token (expected 2 hex chars or '??'): {token!r}"
            raise ValueError(msg)
        else:
            try:
                result.append(int(token, 16))
            except ValueError:
                msg = f"Invalid hex byte in pattern: {token!r}"
                raise ValueError(msg) from None
    return result


def match_byte_pattern(
    data: bytes,
    pattern: str,
    start: int = 0,
    end: int | None = None,
    max_results: int = 100,
) -> list[int]:
    """Search data for a hex byte pattern with wildcard support.

    Pattern syntax: space-separated hex bytes, ``??`` for single-byte wildcard.
    Example: ``'CD ?? 40'`` matches any ``CALL`` to ``0x40xx``.

    Returns list of offsets where the pattern matches, capped at *max_results*.
    Raises ValueError for invalid pattern syntax or negative start.
    """
    if start < 0:
        msg = "Negative start offset"
        raise ValueError(msg)

    parsed = _parse_pattern(pattern)
    pat_len = len(parsed)

    if end is None:
        end = len(data)
    else:
        end = min(end, len(data))

    matches: list[int] = []
    pos = start
    limit = end - pat_len + 1

    while pos < limit and len(matches) < max_results:
        for j, expected in enumerate(parsed):
            if expected is not None and data[pos + j] != expected:
                break
        else:
            matches.append(pos)
        pos += 1

    return matches
