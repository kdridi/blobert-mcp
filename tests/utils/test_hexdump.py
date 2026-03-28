"""Tests for utils/hexdump.py — hex + ASCII dump formatting."""

from __future__ import annotations

from blobert_mcp.utils.hexdump import hexdump


def test_hexdump_empty():
    assert hexdump(b"") == ""


def test_hexdump_single_byte():
    result = hexdump(b"\x41")
    assert result == "00000000  41                                               |A|"


def test_hexdump_full_line():
    data = bytes(range(16))
    result = hexdump(data)
    assert result == (
        "00000000  00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F"
        "  |................|"
    )


def test_hexdump_two_lines():
    data = bytes(range(32))
    lines = hexdump(data).split("\n")
    assert len(lines) == 2
    assert lines[0].startswith("00000000")
    assert lines[1].startswith("00000010")


def test_hexdump_partial_line():
    data = bytes(range(20))
    lines = hexdump(data).split("\n")
    assert len(lines) == 2
    # Second line has only 4 bytes but hex column is padded
    assert "|" in lines[1]


def test_hexdump_offset_format():
    result = hexdump(b"\x00")
    assert result.startswith("00000000")


def test_hexdump_custom_start_offset():
    result = hexdump(b"\x00", start_offset=0x4000)
    assert result.startswith("00004000")


def test_hexdump_printable_ascii():
    data = b"Hello, World!123"
    result = hexdump(data)
    assert "|Hello, World!123|" in result


def test_hexdump_non_printable_as_dot():
    data = bytes([0x00, 0x01, 0x7F, 0xFF])
    result = hexdump(data)
    assert "|....|" in result


def test_hexdump_all_zeros():
    data = b"\x00" * 16
    result = hexdump(data)
    assert "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00" in result
    assert "|................|" in result


def test_hexdump_offset_increments():
    data = bytes(48)
    lines = hexdump(data).split("\n")
    assert lines[0].startswith("00000000")
    assert lines[1].startswith("00000010")
    assert lines[2].startswith("00000020")
