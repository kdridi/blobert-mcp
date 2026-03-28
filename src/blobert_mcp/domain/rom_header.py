"""ROM header parsing for Game Boy cartridges."""

from __future__ import annotations


def parse(data: bytes) -> dict:
    """Parse the Game Boy ROM header from a 0x50-byte header slice.

    Expects bytes from address range 0x0100-0x014F (80 bytes).
    Offsets below are relative to 0x0100.
    """
    if len(data) < 0x50:
        raise ValueError(
            f"Header data too short: need at least 0x50 bytes, got {len(data):#x}"
        )

    title_bytes = data[0x34:0x44]
    title = title_bytes.decode("ascii", errors="replace").rstrip("\x00")

    return {
        "title": title,
        "cgb_flag": data[0x43],
        "sgb_flag": data[0x46],
        "cartridge_type": data[0x47],
        "rom_size": data[0x48],
        "ram_size": data[0x49],
        "old_licensee": data[0x4B],
        "header_checksum": data[0x4D],
        "global_checksum": (data[0x4E] << 8) | data[0x4F],
    }
