"""TDD tests for domain/memory_diff.py — memory diff computation."""

from __future__ import annotations

import pytest

from blobert_mcp.domain.memory_diff import MAX_CHANGES, MemoryChange, diff_memory


class TestMemoryChange:
    def test_fields(self):
        c = MemoryChange(address=0xC000, old=0x00, new=0xFF)
        assert c.address == 0xC000
        assert c.old == 0x00
        assert c.new == 0xFF

    def test_frozen(self):
        c = MemoryChange(address=0xC000, old=0x00, new=0xFF)
        with pytest.raises(AttributeError):
            c.address = 0xC001  # type: ignore[misc]


class TestDiffMemory:
    def test_identical_no_changes(self):
        result = diff_memory(b"\x00\x01\x02\x03", b"\x00\x01\x02\x03", 0xC000)
        assert result == []

    def test_single_change(self):
        result = diff_memory(b"\x00\x01\x02\x03", b"\x00\x01\xff\x03", 0xC000)
        assert len(result) == 1
        assert result[0] == MemoryChange(address=0xC002, old=0x02, new=0xFF)

    def test_multiple_changes(self):
        result = diff_memory(b"\x00\x01\x02\x03", b"\xff\x01\x02\xfe", 0xC000)
        assert len(result) == 2
        assert result[0].address == 0xC000
        assert result[0].old == 0x00
        assert result[0].new == 0xFF
        assert result[1].address == 0xC003
        assert result[1].old == 0x03
        assert result[1].new == 0xFE

    def test_all_bytes_changed(self):
        result = diff_memory(b"\x00\x00\x00\x00", b"\xff\xff\xff\xff", 0xC000)
        assert len(result) == 4

    def test_base_address_applied(self):
        result = diff_memory(b"\x00", b"\x01", 0xFF80)
        assert result[0].address == 0xFF80

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="length"):
            diff_memory(b"\x00\x01", b"\x00", 0xC000)

    def test_empty_inputs(self):
        result = diff_memory(b"", b"", 0xC000)
        assert result == []


class TestMaxChanges:
    def test_value_is_512(self):
        assert MAX_CHANGES == 512

    def test_is_int(self):
        assert isinstance(MAX_CHANGES, int)
