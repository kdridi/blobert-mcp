"""Memory write validation for the Game Boy address space.

No project imports; stdlib only.
"""

from __future__ import annotations

# (start, end) inclusive ranges for writable memory regions
WRITABLE_RANGES: tuple[tuple[int, int], ...] = (
    (0x8000, 0x9FFF),  # VRAM
    (0xC000, 0xDFFF),  # WRAM
    (0xFE00, 0xFE9F),  # OAM
    (0xFF80, 0xFFFE),  # HRAM
)


def validate_write_address(address: int, length: int = 1) -> None:
    """Raise ValueError if any byte is outside writable ranges."""
    end = address + length - 1
    for start, stop in WRITABLE_RANGES:
        if address >= start and end <= stop:
            return
    msg = f"Address 0x{address:04X} (length {length}) is not in a writable range"
    raise ValueError(msg)


def parse_hex_string(data: str) -> bytes:
    """Parse a hex string like 'FF0042' into bytes.

    Raises ValueError on empty string, odd length, or invalid characters.
    """
    if not data:
        msg = "Data hex string must not be empty"
        raise ValueError(msg)
    if len(data) % 2 != 0:
        msg = f"Hex string must have even length, got {len(data)}"
        raise ValueError(msg)
    try:
        return bytes.fromhex(data)
    except ValueError:
        msg = f"Invalid hex characters in data: {data!r}"
        raise ValueError(msg) from None
