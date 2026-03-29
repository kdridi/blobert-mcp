"""TDD tests for memory write validation domain module."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.memory import (
    WRITABLE_RANGES,
    parse_hex_string,
    validate_write_address,
)

# ---------------------------------------------------------------------------
# Writable ranges constant
# ---------------------------------------------------------------------------


class TestWritableRanges:
    def test_contains_vram(self):
        assert (0x8000, 0x9FFF) in WRITABLE_RANGES

    def test_contains_wram(self):
        assert (0xC000, 0xDFFF) in WRITABLE_RANGES

    def test_contains_oam(self):
        assert (0xFE00, 0xFE9F) in WRITABLE_RANGES

    def test_contains_hram(self):
        assert (0xFF80, 0xFFFE) in WRITABLE_RANGES

    def test_exactly_four_ranges(self):
        assert len(WRITABLE_RANGES) == 4


# ---------------------------------------------------------------------------
# validate_write_address
# ---------------------------------------------------------------------------


class TestValidateWriteAddress:
    @pytest.mark.parametrize("addr", [0xC000, 0xC001, 0xDFFF])
    def test_ram_addresses_accepted(self, addr):
        validate_write_address(addr)

    @pytest.mark.parametrize("addr", [0xFF80, 0xFFFE])
    def test_hram_addresses_accepted(self, addr):
        validate_write_address(addr)

    @pytest.mark.parametrize("addr", [0x8000, 0x9FFF])
    def test_vram_addresses_accepted(self, addr):
        validate_write_address(addr)

    @pytest.mark.parametrize("addr", [0xFE00, 0xFE9F])
    def test_oam_addresses_accepted(self, addr):
        validate_write_address(addr)

    def test_rom_address_raises(self):
        with pytest.raises(ValueError):
            validate_write_address(0x0000)

    def test_rom_high_address_raises(self):
        with pytest.raises(ValueError):
            validate_write_address(0x7FFF)

    def test_io_register_address_raises(self):
        with pytest.raises(ValueError):
            validate_write_address(0xFF00)

    def test_io_register_high_raises(self):
        with pytest.raises(ValueError):
            validate_write_address(0xFF7F)

    def test_echo_ram_raises(self):
        with pytest.raises(ValueError):
            validate_write_address(0xE000)

    def test_unusable_address_raises(self):
        with pytest.raises(ValueError):
            validate_write_address(0xFEA0)

    def test_multi_byte_within_range_accepted(self):
        validate_write_address(0xDFF0, length=16)

    def test_multi_byte_exceeding_range_raises(self):
        with pytest.raises(ValueError):
            validate_write_address(0xDFF0, length=32)


# ---------------------------------------------------------------------------
# parse_hex_string
# ---------------------------------------------------------------------------


class TestParseHexString:
    def test_single_byte(self):
        assert parse_hex_string("FF") == b"\xff"

    def test_multiple_bytes(self):
        assert parse_hex_string("FF0042") == b"\xff\x00\x42"

    def test_lowercase_accepted(self):
        assert parse_hex_string("ff") == b"\xff"

    def test_mixed_case(self):
        assert parse_hex_string("aAbB") == b"\xaa\xbb"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_hex_string("")

    def test_odd_length_raises(self):
        with pytest.raises(ValueError):
            parse_hex_string("FFF")

    def test_invalid_chars_raises(self):
        with pytest.raises(ValueError):
            parse_hex_string("GGFF")

    def test_spaces_raises(self):
        with pytest.raises(ValueError):
            parse_hex_string("FF 00")

    def test_returns_bytes_type(self):
        result = parse_hex_string("AB")
        assert isinstance(result, bytes)
