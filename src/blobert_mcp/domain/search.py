"""Byte pattern search and string detection for ROM analysis.

No project imports; stdlib only.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Game Boy custom character encoding (D-020)
# ---------------------------------------------------------------------------
# Common default mapping. Game-specific tables may differ.

GB_CUSTOM_ENCODING: dict[int, str] = {}
# Uppercase letters: 0x80-0x99
for _i, _ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    GB_CUSTOM_ENCODING[0x80 + _i] = _ch
# Lowercase letters: 0xA0-0xB9
for _i, _ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
    GB_CUSTOM_ENCODING[0xA0 + _i] = _ch
# Digits: 0xBA-0xC3
for _i, _ch in enumerate("0123456789"):
    GB_CUSTOM_ENCODING[0xBA + _i] = _ch
# Space
GB_CUSTOM_ENCODING[0x7F] = " "
# Common punctuation
GB_CUSTOM_ENCODING[0xE0] = "!"
GB_CUSTOM_ENCODING[0xE1] = "?"
GB_CUSTOM_ENCODING[0xE2] = "."
GB_CUSTOM_ENCODING[0xE3] = "-"
GB_CUSTOM_ENCODING[0xE4] = ","
GB_CUSTOM_ENCODING[0xE5] = "'"

del _i, _ch  # clean up loop variables


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


def find_text_strings(
    data: bytes,
    min_length: int = 4,
    encoding: str = "ascii",
    max_results: int = 200,
) -> list[tuple[int, str]]:
    """Scan data for text strings using the specified encoding.

    Supported encodings: ``'ascii'`` (printable 0x20-0x7E), ``'gb_custom'``
    (common Game Boy character mapping).

    Returns list of ``(offset, decoded_text)`` tuples, capped at *max_results*.
    Raises ValueError for unsupported encoding or invalid min_length.
    """
    if min_length < 1:
        msg = f"min_length must be >= 1, got {min_length}"
        raise ValueError(msg)

    if encoding == "ascii":

        def _is_valid(byte: int) -> str | None:
            return chr(byte) if 0x20 <= byte <= 0x7E else None

    elif encoding == "gb_custom":

        def _is_valid(byte: int) -> str | None:
            return GB_CUSTOM_ENCODING.get(byte)

    else:
        msg = f"Unsupported encoding: {encoding!r}"
        raise ValueError(msg)

    results: list[tuple[int, str]] = []
    i = 0
    while i < len(data) and len(results) < max_results:
        ch = _is_valid(data[i])
        if ch is None:
            i += 1
            continue
        # Start of a potential string
        start = i
        chars: list[str] = [ch]
        i += 1
        while i < len(data):
            ch = _is_valid(data[i])
            if ch is None:
                break
            chars.append(ch)
            i += 1
        if len(chars) >= min_length:
            results.append((start, "".join(chars)))

    return results
