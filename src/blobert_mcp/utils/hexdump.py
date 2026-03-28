"""Hex + ASCII dump formatting."""

from __future__ import annotations


def hexdump(data: bytes, start_offset: int = 0) -> str:
    """Format bytes as a hex dump with ASCII sidebar.

    Format per line: OFFSET  HH HH HH ... HH  |ASCII...........|
    16 bytes per line. Non-printable characters shown as '.'.
    """
    if not data:
        return ""

    lines: list[str] = []
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        offset = start_offset + i

        hex_part = " ".join(f"{b:02X}" for b in chunk)
        hex_part = hex_part.ljust(47)

        ascii_part = "".join(
            chr(b) if 0x20 <= b <= 0x7E else "." for b in chunk
        )

        lines.append(f"{offset:08X}  {hex_part}  |{ascii_part}|")

    return "\n".join(lines)
