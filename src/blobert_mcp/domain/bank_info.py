"""MBC type detection and ROM bank count calculation."""

from __future__ import annotations

_CARTRIDGE_TYPES: dict[int, dict[str, object]] = {
    0x00: {"name": "ROM ONLY", "mbc": None, "ram": False, "battery": False},
    0x01: {"name": "MBC1", "mbc": "MBC1", "ram": False, "battery": False},
    0x02: {"name": "MBC1+RAM", "mbc": "MBC1", "ram": True, "battery": False},
    0x03: {
        "name": "MBC1+RAM+BATTERY",
        "mbc": "MBC1",
        "ram": True,
        "battery": True,
    },
    0x0F: {
        "name": "MBC3+TIMER+BATTERY",
        "mbc": "MBC3",
        "ram": False,
        "battery": True,
        "timer": True,
    },
    0x10: {
        "name": "MBC3+TIMER+RAM+BATTERY",
        "mbc": "MBC3",
        "ram": True,
        "battery": True,
        "timer": True,
    },
    0x11: {"name": "MBC3", "mbc": "MBC3", "ram": False, "battery": False},
    0x12: {"name": "MBC3+RAM", "mbc": "MBC3", "ram": True, "battery": False},
    0x13: {
        "name": "MBC3+RAM+BATTERY",
        "mbc": "MBC3",
        "ram": True,
        "battery": True,
    },
    0x19: {"name": "MBC5", "mbc": "MBC5", "ram": False, "battery": False},
    0x1A: {"name": "MBC5+RAM", "mbc": "MBC5", "ram": True, "battery": False},
    0x1B: {
        "name": "MBC5+RAM+BATTERY",
        "mbc": "MBC5",
        "ram": True,
        "battery": True,
    },
    0x1C: {
        "name": "MBC5+RUMBLE",
        "mbc": "MBC5",
        "ram": False,
        "battery": False,
        "rumble": True,
    },
    0x1D: {
        "name": "MBC5+RUMBLE+RAM",
        "mbc": "MBC5",
        "ram": True,
        "battery": False,
        "rumble": True,
    },
    0x1E: {
        "name": "MBC5+RUMBLE+RAM+BATTERY",
        "mbc": "MBC5",
        "ram": True,
        "battery": True,
        "rumble": True,
    },
}


def detect_mbc_type(cartridge_byte: int) -> dict[str, object]:
    """Return MBC type info for a cartridge type byte."""
    if cartridge_byte in _CARTRIDGE_TYPES:
        return dict(_CARTRIDGE_TYPES[cartridge_byte])
    return {"name": "UNKNOWN", "mbc": None, "ram": False, "battery": False}


def calculate_bank_count(rom_size_byte: int) -> int:
    """Return total ROM bank count from the ROM size header byte."""
    return 2 << rom_size_byte
