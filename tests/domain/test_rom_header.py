"""Tests for domain/rom_header.py — ROM header parsing."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.rom_header import parse


def _make_header(
    *,
    title: bytes = b"",
    cgb: int = 0,
    sgb: int = 0,
    cart_type: int = 0,
    rom_size: int = 0,
    ram_size: int = 0,
    licensee: int = 0,
    header_cksum: int = 0,
    global_cksum: int = 0,
) -> bytes:
    """Build a synthetic 0x50-byte header slice (0x0100-0x014F)."""
    data = bytearray(0x50)
    for i, b in enumerate(title[:16]):
        data[0x34 + i] = b
    data[0x43] = cgb
    data[0x46] = sgb
    data[0x47] = cart_type
    data[0x48] = rom_size
    data[0x49] = ram_size
    data[0x4B] = licensee
    data[0x4D] = header_cksum
    data[0x4E] = (global_cksum >> 8) & 0xFF
    data[0x4F] = global_cksum & 0xFF
    return bytes(data)


def test_parse_title_basic():
    header = _make_header(title=b"TESTGAME")
    result = parse(header)
    assert result["title"] == "TESTGAME"


def test_parse_title_null_terminated():
    header = _make_header(title=b"HELLO\x00\x00\x00")
    result = parse(header)
    assert result["title"] == "HELLO"


def test_parse_title_non_ascii():
    header = _make_header(title=b"\x80\x81\x82")
    result = parse(header)
    # Non-ASCII bytes are replaced
    assert "\ufffd" in result["title"]


def test_parse_cartridge_type():
    header = _make_header(cart_type=0x13)
    result = parse(header)
    assert result["cartridge_type"] == 0x13


def test_parse_rom_size():
    header = _make_header(rom_size=0x05)
    result = parse(header)
    assert result["rom_size"] == 0x05


def test_parse_ram_size():
    header = _make_header(ram_size=0x02)
    result = parse(header)
    assert result["ram_size"] == 0x02


def test_parse_cgb_flag():
    header = _make_header(cgb=0x80)
    result = parse(header)
    assert result["cgb_flag"] == 0x80


def test_parse_sgb_flag():
    header = _make_header(sgb=0x03)
    result = parse(header)
    assert result["sgb_flag"] == 0x03


def test_parse_old_licensee():
    header = _make_header(licensee=0x33)
    result = parse(header)
    assert result["old_licensee"] == 0x33


def test_parse_header_checksum():
    header = _make_header(header_cksum=0xE7)
    result = parse(header)
    assert result["header_checksum"] == 0xE7


def test_parse_global_checksum():
    header = _make_header(global_cksum=0xABCD)
    result = parse(header)
    assert result["global_checksum"] == 0xABCD


def test_parse_too_short_raises():
    with pytest.raises(ValueError, match="too short"):
        parse(b"\x00" * 0x4F)


def test_parse_minimal_valid():
    header = _make_header()
    result = parse(header)
    assert result["title"] == ""
    assert result["cartridge_type"] == 0
